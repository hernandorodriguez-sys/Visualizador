import serial
import time
import threading
import queue
import logging
from .config import DEBUG_MODE, BAUD_RATE, SAMPLE_RATE, POST_R_DELAY_SAMPLES, MIN_PEAK_DISTANCE, MIN_PEAK_HEIGHT, PEAK_WIDTH_MIN, PEAK_PROMINENCE
import numpy as np
from scipy import signal
from .data_types import ADCData

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SerialReaderESP32:
    def __init__(self, port, baud_rate, max_connection_attempts=5):
        self.port = port
        self.baud_rate = baud_rate
        self.max_connection_attempts = max_connection_attempts
        self.connection_attempts = 0
        self.ser = None
        self.running = False
        self.total_bytes_received = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.sync_buffer = []

        # Processing thread components
        self.processing_queue = queue.Queue(maxsize=15000)
        self.processing_thread = None
        self.signal_processing_service = None

    def connect(self):
        if self.connection_attempts >= self.max_connection_attempts:
            return False

        for attempt in range(self.max_connection_attempts - self.connection_attempts):
            try:
                if self.ser:
                    self.ser.close()
                print(f"[ESP32] Intentando conectar a {self.port}... (intento {self.connection_attempts + attempt + 1})")
                self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
                time.sleep(2)

                self.ser.flushInput()
                self.ser.flushOutput()

                print(f"[ESP32] Conexion establecida en {self.port}")
                self.connection_attempts = 0  # Reset on success
                return True
            except Exception as e:
                print(f"[ESP32] Error en intento {self.connection_attempts + attempt + 1}: {e}")
                time.sleep(1)

        self.connection_attempts += (self.max_connection_attempts - self.connection_attempts)
        return False

    def send_lead_command(self, lead_name):
        """Envía comando de cambio de derivación al ESP32"""
        if self.ser and self.ser.is_open:
            try:
                cmd = f"LEAD_{lead_name}\n"
                self.ser.write(cmd.encode())
                print(f"[ESP32] Comando enviado: {cmd.strip()}")
            except Exception as e:
                print(f"[ESP32] ❌ Error enviando comando: {e}")

    def decode_packet(self, pkt):
        """Decodifica paquete binario de 4 bytes con checksum"""
        if len(pkt) != 4:
            self.invalid_packets += 1
            return None

        start, lsb, msb, checksum = pkt

        if start != 0xAA:
            self.invalid_packets += 1
            return None

        expected_checksum = start ^ lsb ^ msb
        if checksum != expected_checksum:
            self.invalid_packets += 1
            return None

        val = (msb << 8) | lsb
        voltage = val * (3.3 / 4095.0)

        self.valid_packets += 1
        return voltage

    def set_signal_processing_service(self, service):
        """Set the signal processing service for the processing thread"""
        self.signal_processing_service = service

    def _processing_worker(self):
        """Processing thread that sends decoded data to filter functions"""
        while self.running:
            try:
                # Get decoded data from processing queue
                voltage, metadata = self.processing_queue.get(timeout=0.1)

                # Send to signal processing service (filter functions)
                if self.signal_processing_service:
                    adc_data = ADCData(
                        timestamp=int(time.time() * 1000),
                        voltage=voltage,
                        source='esp32',
                        metadata=metadata or {}
                    )
                    self.signal_processing_service.process_data(adc_data)

                self.processing_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[ESP32] Processing thread error: {e}")
                time.sleep(0.01)

    def read_data(self, adc_service):
        """Lee datos ECG usando sincronización robusta"""
        print("[ESP32] Iniciando lectura de datos ECG...")
        last_log_time = time.time()

        while self.running:
            try:
                if not self.ser or not self.ser.is_open:
                    if self.connection_attempts >= self.max_connection_attempts:
                        time.sleep(1)  # Just wait, don't try to reconnect
                        continue
                    if not self.connect():
                        time.sleep(1)
                        continue

                if self.ser.in_waiting > 0:
                    raw_bytes = self.ser.read(self.ser.in_waiting)
                    self.total_bytes_received += len(raw_bytes)

                    try:
                        text = raw_bytes.decode('utf-8', errors='ignore')

                        if "LEAD_CHANGE:" in text:
                            parts = text.split("LEAD_CHANGE:")[1].split(",")
                            if len(parts) >= 2:
                                lead_idx = int(parts[0].strip())
                                lead_name = parts[1].strip()
                                metadata = {'lead_change': {'index': lead_idx, 'name': lead_name}}
                                adc_service.on_esp32_data(0.0, metadata)  # Send metadata without voltage
                                print(f"[ESP32] Cambio de derivacion: {lead_name}")

                        if "R_PEAK:" in text:
                            metadata = {'r_peak': True}
                            adc_service.on_esp32_data(0.0, metadata)  # Send metadata without voltage
                            if DEBUG_MODE:
                                print(f"[ESP32] Pico R detectado")

                        if "DISPARO:" in text:
                            metadata = {'disparo': text.strip()}
                            adc_service.on_esp32_data(0.0, metadata)  # Send metadata without voltage
                            if DEBUG_MODE:
                                print(f"[ESP32] {text.strip()}")
                    except:
                        pass

                    self.sync_buffer.extend(raw_bytes)

                    while len(self.sync_buffer) >= 4:
                        start_idx = -1
                        for i, byte in enumerate(self.sync_buffer):
                            if byte == 0xAA:
                                start_idx = i
                                break

                        if start_idx == -1:
                            self.sync_buffer.clear()
                            break

                        if start_idx > 0:
                            self.sync_buffer = self.sync_buffer[start_idx:]

                        if len(self.sync_buffer) >= 4:
                            packet = self.sync_buffer[:4]
                            voltage = self.decode_packet(packet)

                            if voltage is not None:
                                # Send raw voltage data to ADC service (for UI consumption)
                                adc_service.on_esp32_data(voltage)

                                # Put decoded data in processing queue for filter functions
                                # Non-blocking: drop oldest if full to keep latest data
                                try:
                                    self.processing_queue.put_nowait((voltage, None))
                                except queue.Full:
                                    # Drop oldest to make room for new
                                    try:
                                        self.processing_queue.get_nowait()
                                        self.processing_queue.put_nowait((voltage, None))
                                    except queue.Empty:
                                        pass

                            self.sync_buffer = self.sync_buffer[4:]
                        else:
                            break

                    if len(self.sync_buffer) > 100:
                        self.sync_buffer = self.sync_buffer[-50:]

                    # Periodic logging every 10 seconds
                    current_time = time.time()
                    if current_time - last_log_time > 10:
                        try:
                            logger.info(f"ESP32 stats - Bytes received: {self.total_bytes_received}, Valid packets: {self.valid_packets}, Invalid packets: {self.invalid_packets}, Processing queue size: {self.processing_queue.qsize()}")
                        except:
                            pass
                        last_log_time = current_time

                time.sleep(0.0005)

            except Exception as e:
                if DEBUG_MODE:
                    print(f"[ESP32] ❌ Error en lectura: {e}")
                time.sleep(1)

    def start(self, adc_service):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.read_data, args=(adc_service,), daemon=True)
        self.thread.start()

        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.processing_thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser:
            self.ser.close()
        # Clean queue and reset counters
        self.processing_queue = queue.Queue(maxsize=15000)
        self.total_bytes_received = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.sync_buffer.clear()

class SerialReaderArduino:
    def __init__(self, port, baud_rate, max_connection_attempts=5):
        self.port = port
        self.baud_rate = baud_rate
        self.max_connection_attempts = max_connection_attempts
        self.connection_attempts = 0
        self.ser = None
        self.running = False

    def connect(self):
        if self.connection_attempts >= self.max_connection_attempts:
            return False

        for attempt in range(self.max_connection_attempts - self.connection_attempts):
            try:
                if self.ser:
                    self.ser.close()
                print(f"[ARDUINO] Intentando conectar a {self.port}... (intento {self.connection_attempts + attempt + 1})")
                self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
                time.sleep(2)

                self.ser.flushInput()
                self.ser.flushOutput()

                print(f"[ARDUINO] Conexion establecida en {self.port}")
                self.connection_attempts = 0  # Reset on success
                return True
            except Exception as e:
                print(f"[ARDUINO] Error en intento {self.connection_attempts + attempt + 1}: {e}")
                time.sleep(1)

        self.connection_attempts += (self.max_connection_attempts - self.connection_attempts)
        return False

    def send_command(self, command):
        """Envía comandos al Arduino"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode())
                print(f"[ARDUINO] Comando enviado: {command}")
            except Exception as e:
                print(f"[ARDUINO] ❌ Error enviando comando: {e}")

    def process_arduino_data(self, line, adc_service):
        """Procesa datos del Arduino (formato CSV)"""
        try:
            parts = line.strip().split(',')
            if len(parts) == 7:
                timestamp = int(parts[0])
                vcap = float(parts[1])
                corriente = float(parts[2])
                e_f1 = float(parts[3])
                e_f2 = float(parts[4])
                e_total = float(parts[5])
                estado = parts[6]

                # Send energy data to ADC service
                metadata = {
                    'energia': {
                        'vcap': vcap,
                        'corriente': corriente,
                        'e_f1': e_f1,
                        'e_f2': e_f2,
                        'e_total': e_total,
                        'estado': estado
                    }
                }
                adc_service.on_arduino_data(timestamp, vcap, metadata)

        except Exception as e:
            if DEBUG_MODE:
                print(f"[ARDUINO] Error procesando datos: {e}")

    def read_data(self, adc_service):
        print("[ARDUINO] Iniciando lectura de datos de energia...")

        while self.running:
            try:
                if not self.ser or not self.ser.is_open:
                    if self.connection_attempts >= self.max_connection_attempts:
                        time.sleep(1)  # Just wait, don't try to reconnect
                        continue
                    if not self.connect():
                        time.sleep(1)
                        continue

                if self.ser.in_waiting > 0:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore')
                        if ',' in line and line.count(',') >= 6:
                            self.process_arduino_data(line, adc_service)
                    except Exception as e:
                        if DEBUG_MODE:
                            print(f"[ARDUINO] Error leyendo línea: {e}")

                time.sleep(0.01)

            except Exception as e:
                if DEBUG_MODE:
                    print(f"[ARDUINO] ❌ Error en lectura: {e}")
                time.sleep(1)

    def start(self, adc_service):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.read_data, args=(adc_service,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()