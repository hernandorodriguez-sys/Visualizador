import threading
import queue
import time
from typing import NamedTuple, Optional
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .config import SERIAL_PORT_ESP32, SERIAL_PORT_ARDUINO, BAUD_RATE

class ADCData(NamedTuple):
    """Data structure for ADC readings"""
    timestamp: int
    voltage: float
    source: str  # 'esp32' or 'arduino'
    metadata: dict = None  # Additional data like lead changes, energies, etc.

class ADCService:
    """Service responsible for ADC data acquisition from ESP32 and Arduino"""

    def __init__(self):
        self.running = False
        self.thread = None

        # Communication queues
        self.data_queue = queue.Queue(maxsize=10000)  # For ADC data output
        self.command_queue = queue.Queue()  # For incoming commands

        # Service references for communication
        self.signal_processing_service = None
        self.ui_service = None

        # Serial readers
        self.esp32_reader = SerialReaderESP32(SERIAL_PORT_ESP32, BAUD_RATE)
        self.arduino_reader = SerialReaderArduino(SERIAL_PORT_ARDUINO, BAUD_RATE)

        # Status
        self.esp32_connected = False
        self.arduino_connected = False

        print("ADC Data Acquisition Service initialized")

    def set_services(self, signal_processing_service, ui_service):
        """Set references to other services for communication"""
        self.signal_processing_service = signal_processing_service
        self.ui_service = ui_service

    def start(self):
        """Start the ADC service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

            # Start serial readers
            self.esp32_reader.start(self)
            time.sleep(1)
            self.arduino_reader.start(self)

            print("ADC Data Acquisition Service started")

    def stop(self):
        """Stop the ADC service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

        self.esp32_reader.stop()
        self.arduino_reader.stop()
        print("ADC Data Acquisition Service stopped")

    def send_command(self, command: str, target: str = "esp32"):
        """Send command to serial devices"""
        self.command_queue.put((command, target))

    def get_data(self, timeout: float = 0.1) -> Optional[ADCData]:
        """Get next ADC data from queue"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _run(self):
        """Main service loop"""
        while self.running:
            try:
                # Process commands
                self._process_commands()

                # Check connection status
                self.esp32_connected = self.esp32_reader.running and self.esp32_reader.ser and self.esp32_reader.ser.is_open
                self.arduino_connected = self.arduino_reader.running and self.arduino_reader.ser and self.arduino_reader.ser.is_open

                time.sleep(0.01)  # Small delay

            except Exception as e:
                print(f"ADC Service error: {e}")
                time.sleep(0.1)

    def _process_commands(self):
        """Process pending commands"""
        try:
            while True:
                command, target = self.command_queue.get_nowait()
                if target == "esp32":
                    self.esp32_reader.send_lead_command(command)
                elif target == "arduino":
                    self.arduino_reader.send_command(command)
        except queue.Empty:
            pass

    # Callback methods for serial readers to send data
    def on_esp32_data(self, voltage: float, metadata: dict = None):
        """Callback for ESP32 data"""
        data = ADCData(
            timestamp=int(time.time() * 1000),
            voltage=voltage,
            source='esp32',
            metadata=metadata or {}
        )

        # Send to signal processing service
        if self.signal_processing_service:
            self.signal_processing_service.process_data(data)

        # Send to UI service
        if self.ui_service:
            self.ui_service.add_adc_data(data)

        # Keep in our own queue for external access
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            # Remove oldest data if queue is full
            try:
                self.data_queue.get_nowait()
                self.data_queue.put_nowait(data)
            except queue.Empty:
                pass

    def on_arduino_data(self, timestamp: int, voltage: float, metadata: dict = None):
        """Callback for Arduino data"""
        data = ADCData(
            timestamp=timestamp,
            voltage=voltage,
            source='arduino',
            metadata=metadata or {}
        )

        # Send to UI service (Arduino data goes directly to UI)
        if self.ui_service:
            self.ui_service.add_adc_data(data)

        # Keep in our own queue for external access
        try:
            self.data_queue.put_nowait(data)
        except queue.Full:
            try:
                self.data_queue.get_nowait()
                self.data_queue.put_nowait(data)
            except queue.Empty:
                pass