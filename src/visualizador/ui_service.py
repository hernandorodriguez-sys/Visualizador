import threading
import queue
import time
from typing import Optional
from collections import deque
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer, pyqtSlot, QObject

# Import MainWindow inside the method to avoid circular import
from .plot_utils import setup_plot, update_plot
from .utils import get_current_lead
from .data_recorder import DataRecorder

class UIService(QObject):
    """Service responsible for UI updates and plot management"""

    def __init__(self):
        super().__init__()
        self.running = False
        self.thread = None

        # Communication queues
        self.processed_data_queue = queue.Queue(maxsize=10000)  # Processed signal data input
        self.adc_data_queue = queue.Queue(maxsize=10000)  # ADC data input for metadata

        # UI components
        self.app = None
        self.window = None
        self.timer = None

        # Data buffers (similar to DataManager but simplified)
        self.voltage_buffer = deque(maxlen=10000)
        self.filtered_buffer = deque(maxlen=10000)
        self.baseline_buffer = deque(maxlen=10000)
        self.antialiased_buffer = deque(maxlen=10000)
        self.time_buffer = deque(maxlen=10000)
        self.sample_count = 0

        # Status data
        self.esp32_connected = False
        self.arduino_connected = False
        self.current_lead_index = 0
        self.energia_carga_actual = 0.0
        self.energia_fase1_actual = 0.0
        self.energia_fase2_actual = 0.0
        self.energia_total_ciclo = 0.0
        self.discharge_events = []
        self.last_discharge_time = 0
        self.last_r_peak_time = 0

        # Plot settings
        self.plot_y_min = -0.5
        self.plot_y_max = 4.0
        self.plot_window_size = 1500
        self.plot_time_axis = False
        self.signal_gain = 1.0

        # Data recorder
        self.data_recorder = DataRecorder()

        print("UI Service initialized")

    def start(self, adc_service):
        """Start the UI service"""
        if not self.running:
            self.running = True

            # Start data recorder
            self.data_recorder.start_recording()

            # Initialize PyQt application
            self.app = QApplication([])

            # Import MainWindow here to avoid circular import
            from .ui_main import MainWindow

            # Create main window
            self.window = MainWindow(self, adc_service.esp32_reader, adc_service.arduino_reader)
            self.window.show()

            # Start update timer
            self.timer = QTimer()
            self.timer.timeout.connect(self._update_ui)
            self.timer.start(20)  # Update every 20ms for better real-time performance

            print("UI Service started")

    def stop(self):
        """Stop the UI service"""
        self.running = False
        if self.timer:
            self.timer.stop()
        self.data_recorder.close()
        print("UI Service stopped")

    def run_app(self):
        """Run the Qt application (blocking)"""
        if self.app:
            self.app.exec()

    def add_processed_data(self, processed_data):
        """Add processed signal data to UI"""
        try:
            self.processed_data_queue.put_nowait(processed_data)
        except queue.Full:
            try:
                self.processed_data_queue.get_nowait()
                self.processed_data_queue.put_nowait(processed_data)
            except queue.Empty:
                pass

    def add_adc_data(self, adc_data):
        """Add ADC data for metadata updates"""
        try:
            self.adc_data_queue.put_nowait(adc_data)
        except queue.Full:
            try:
                self.adc_data_queue.get_nowait()
                self.adc_data_queue.put_nowait(adc_data)
            except queue.Empty:
                pass

    def update_connection_status(self, esp32_connected: bool, arduino_connected: bool):
        """Update device connection status"""
        self.esp32_connected = esp32_connected
        self.arduino_connected = arduino_connected

    def _process_incoming_data(self, max_items_per_update=500):
        """Process incoming data from queues (limited per update cycle for responsiveness)"""
        items_processed = 0

        # Process processed signal data (limit to prevent UI freezing)
        try:
            while items_processed < max_items_per_update:
                processed_data = self.processed_data_queue.get_nowait()

                # Apply gain to raw voltage
                voltage_with_gain = processed_data.raw_voltage * self.signal_gain

                # Store in buffers
                self.voltage_buffer.append(voltage_with_gain)
                self.filtered_buffer.append(processed_data.filtered_voltage)
                self.baseline_buffer.append(processed_data.baseline)
                self.antialiased_buffer.append(processed_data.antialiased_voltage)
                self.time_buffer.append(processed_data.sample_count)
                self.sample_count = processed_data.sample_count

                self.processed_data_queue.task_done()
                items_processed += 1

        except queue.Empty:
            pass

        # Process ADC metadata (limit to prevent UI freezing)
        try:
            while items_processed < max_items_per_update:
                adc_data = self.adc_data_queue.get_nowait()

                if adc_data.source == 'esp32' and adc_data.metadata:
                    if 'lead_change' in adc_data.metadata:
                        self.current_lead_index = adc_data.metadata['lead_change']['index']
                    if 'r_peak' in adc_data.metadata:
                        self.last_r_peak_time = adc_data.timestamp

                elif adc_data.source == 'arduino' and adc_data.metadata and 'energia' in adc_data.metadata:
                    energia = adc_data.metadata['energia']
                    estado = energia['estado']

                    if estado == "CARGA":
                        self.energia_carga_actual = energia['e_total']
                    elif estado.startswith("DESCARGA"):
                        self.energia_fase1_actual = energia['e_f1']
                        self.energia_fase2_actual = energia['e_f2']
                        self.energia_total_ciclo = energia['e_total']

                        if estado == "DESCARGA_F1" and (adc_data.timestamp - self.last_discharge_time > 1000):
                            tiempo_desde_r = adc_data.timestamp - self.last_r_peak_time if self.last_r_peak_time > 0 else 0
                            self.discharge_events.append((self.sample_count, adc_data.timestamp, tiempo_desde_r))
                            self.last_discharge_time = adc_data.timestamp

                    # Record to CSV
                    self.data_recorder.write_row(
                        energia['timestamp'] if 'timestamp' in energia else adc_data.timestamp,
                        energia['vcap'], energia['corriente'],
                        energia['e_f1'], energia['e_f2'], energia['e_total'], estado
                    )

                self.adc_data_queue.task_done()
                items_processed += 1

        except queue.Empty:
            pass

    @pyqtSlot()
    def _update_ui(self):
        """Update the UI components"""
        if not self.window:
            return

        # Process incoming data
        self._process_incoming_data()

        # Update plot
        if hasattr(self.window, 'line_raw') and hasattr(self.window, 'status_text') and hasattr(self.window, 'ax'):
            update_plot(self, self.window.line_raw, self.window.status_text, self.window.ax)
            self.window.canvas.draw()

        # Update status widgets
        current_lead = get_current_lead(self.current_lead_index)
        discharge_list = list(self.discharge_events)
        last_discharge_time = f"{discharge_list[-1][2]:.0f} ms" if discharge_list else "N/A"

        # Update device status
        if hasattr(self.window, 'device_status'):
            self.window.device_status.update_status(
                esp32_connected=self.esp32_connected,
                arduino_connected=self.arduino_connected
            )

        # Update cardioversor status
        if hasattr(self.window, 'cardioversor_status'):
            self.window.cardioversor_status.update_status(
                current_lead=current_lead,
                charge_energy=self.energia_carga_actual,
                phase1_energy=self.energia_fase1_actual,
                phase2_energy=self.energia_fase2_actual,
                total_energy=self.energia_total_ciclo,
                last_discharge_time=last_discharge_time,
                total_discharges=len(self.discharge_events)
            )

        # Update data recorder status
        if hasattr(self.window, 'data_recorder_control'):
            self.window.data_recorder_control.update_status()