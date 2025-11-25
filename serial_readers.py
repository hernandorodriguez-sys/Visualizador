import serial
import time
from config import DEBUG_MODE, BAUD_RATE, SAMPLE_RATE, POST_R_DELAY_SAMPLES, MIN_PEAK_DISTANCE, MIN_PEAK_HEIGHT, PEAK_WIDTH_MIN, PEAK_PROMINENCE
from filters import BaselineEMA
import numpy as np
from scipy import signal

class SerialReaderESP32:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.running = False
        self.total_bytes_received = 0
        self.valid_packets = 0
        self.invalid_packets = 0
        self.sync_buffer = []

    def connect(self):
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if self.ser:
                    self.ser.close()
                print(f"[ESP32] Intentando conectar a {self.port}... (intento {attempt + 1})")
                self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
                time.sleep(2)

                self.ser.flushInput()
                self.ser.flushOutput()

                print(f"[ESP32] Conexion establecida en {self.port}")
                return True
            except Exception as e:
                print(f"[ESP32] Error en intento {attempt + 1}: {e}")
                time.sleep(1)
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

    def read_data(self, data_manager):
        """Lee datos ECG usando sincronización robusta"""
        print("[ESP32] Iniciando lectura de datos ECG...")

        while self.running:
            try:
                if not self.ser or not self.ser.is_open:
                    data_manager.esp32_connected = False
                    if not self.connect():
                        time.sleep(1)
                        continue

                data_manager.esp32_connected = True

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
                                with data_manager.data_lock:
                                    data_manager.current_lead_index = lead_idx
                                print(f"[ESP32] Cambio de derivacion: {lead_name}")

                        if "R_PEAK:" in text:
                            with data_manager.data_lock:
                                data_manager.last_r_peak_time = int(time.time() * 1000)
                            if DEBUG_MODE:
                                print(f"[ESP32] Pico R detectado")

                        if "DISPARO:" in text:
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
                                filtered_voltage, baseline = data_manager.baseline_filter.process_sample(voltage)

                                with data_manager.data_lock:
                                    data_manager.voltage_buffer.append(voltage)
                                    data_manager.filtered_buffer.append(filtered_voltage)
                                    data_manager.baseline_buffer.append(baseline)
                                    data_manager.time_buffer.append(data_manager.sample_count)
                                    data_manager.sample_count += 1

                            self.sync_buffer = self.sync_buffer[4:]
                        else:
                            break

                    if len(self.sync_buffer) > 100:
                        self.sync_buffer = self.sync_buffer[-50:]
                time.sleep(0.0005)

            except Exception as e:
                if DEBUG_MODE:
                    print(f"[ESP32] ❌ Error en lectura: {e}")
                data_manager.esp32_connected = False
                time.sleep(1)

    def start(self, data_manager):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.read_data, args=(data_manager,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()

class SerialReaderArduino:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.running = False

    def connect(self):
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if self.ser:
                    self.ser.close()
                print(f"[ARDUINO] Intentando conectar a {self.port}... (intento {attempt + 1})")
                self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
                time.sleep(2)

                self.ser.flushInput()
                self.ser.flushOutput()

                print(f"[ARDUINO] Conexion establecida en {self.port}")
                return True
            except Exception as e:
                print(f"[ARDUINO] Error en intento {attempt + 1}: {e}")
                time.sleep(1)
        return False

    def send_command(self, command):
        """Envía comandos al Arduino"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode())
                print(f"[ARDUINO] Comando enviado: {command}")
            except Exception as e:
                print(f"[ARDUINO] ❌ Error enviando comando: {e}")

    def process_arduino_data(self, line, data_manager):
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

                with data_manager.data_lock:
                    if estado == "CARGA":
                        data_manager.energia_carga_actual = e_total
                    elif estado == "ESPERANDO":
                        pass
                    elif estado.startswith("DESCARGA"):
                        data_manager.energia_fase1_actual = e_f1
                        data_manager.energia_fase2_actual = e_f2
                        data_manager.energia_total_ciclo = e_total

                    # Capturar datos para gráfica de descarga bifásica
                    with data_manager.data_lock:
                        if estado == "DESCARGA_F1" and (timestamp - data_manager.last_discharge_time > 1000):
                            data_manager.descarga_voltage_buffer.clear()
                            data_manager.descarga_time_buffer.clear()
                            data_manager.descarga_timestamp_inicio = timestamp

                        if data_manager.descarga_timestamp_inicio > 0:
                            tiempo_relativo = timestamp - data_manager.descarga_timestamp_inicio
                            data_manager.descarga_voltage_buffer.append(vcap)
                            data_manager.descarga_time_buffer.append(tiempo_relativo)

                        if estado == "DESCARGA_F1" and (timestamp - data_manager.last_discharge_time > 1000):
                            tiempo_desde_r = timestamp - data_manager.last_r_peak_time if data_manager.last_r_peak_time > 0 else 0
                            data_manager.discharge_events.append((data_manager.sample_count, timestamp, tiempo_desde_r))
                            data_manager.last_discharge_time = timestamp

                data_manager.write_csv_row(timestamp, vcap, corriente, e_f1, e_f2, e_total, estado)

        except Exception as e:
            if DEBUG_MODE:
                print(f"[ARDUINO] Error procesando datos: {e}")

    def read_data(self, data_manager):
        print("[ARDUINO] Iniciando lectura de datos de energia...")

        while self.running:
            try:
                if not self.ser or not self.ser.is_open:
                    data_manager.arduino_connected = False
                    if not self.connect():
                        time.sleep(1)
                        continue

                data_manager.arduino_connected = True

                if data_manager.force_charge:
                    self.send_command("FORCE_CHARGE")
                    data_manager.force_charge = False
                if data_manager.force_discharge:
                    self.send_command("FORCE_DISCHARGE")
                    data_manager.force_discharge = False

                if self.ser.in_waiting > 0:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore')
                        if ',' in line and line.count(',') >= 6:
                            self.process_arduino_data(line, data_manager)
                    except Exception as e:
                        if DEBUG_MODE:
                            print(f"[ARDUINO] Error leyendo línea: {e}")

                time.sleep(0.01)

            except Exception as e:
                if DEBUG_MODE:
                    print(f"[ARDUINO] ❌ Error en lectura: {e}")
                data_manager.arduino_connected = False
                time.sleep(1)

    def start(self, data_manager):
        self.running = True
        import threading
        self.thread = threading.Thread(target=self.read_data, args=(data_manager,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()