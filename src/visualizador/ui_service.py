import threading
import queue
import time
import logging
from typing import Optional, NamedTuple
from collections import deque
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer, pyqtSlot, QObject

# Import MainWindow inside the method to avoid circular import
from .plot_utils import setup_plot, update_plot
from .data_recorder import DataRecorder
from .utils import get_current_lead
from .r_peak_detector import calculate_bpm
from .config import SAMPLE_RATE

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessedData(NamedTuple):
    """Data structure for processed signal data"""
    timestamp: int
    raw_voltage: float
    sample_count: int
    peaks: list = None
    metadata: dict = None

class UIService(QObject):
    """Service responsible for UI updates and plot management"""

    def __init__(self):
        super().__init__()
        self.running = False
        self.thread = None

        # Communication queues
        self.processed_data_queue = queue.Queue(maxsize=30000)  # Processed signal data input
        self.adc_data_queue = queue.Queue(maxsize=30000)  # ADC data input for metadata
        self.recording_queue = queue.Queue(maxsize=30000)  # Data to record to file

        # Recording thread
        self.recording_thread = None

        # UI components
        self.app = None
        self.window = None
        self.timer = None

        # Data buffers (similar to DataManager but simplified)
        self.voltage_buffer = deque(maxlen=15000)
        self.time_buffer = deque(maxlen=15000)
        self.r_peak_buffer = deque(maxlen=100)  # Store recent R-peak positions
        self.sample_count = 0
        self.ecg_record_counter = 0
        self.last_log_time = time.time()

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
        self.current_bpm = 0.0

        # Plot settings
        self.plot_y_min = -2.0
        self.plot_y_max = 2.0
        self.plot_window_size = 1500
        self.plot_time_window = 0.75  # 0.75 seconds (1500 samples at 2000 Hz)
        self.plot_time_axis = False
        self.signal_gain = 1.0
        self.signal_offset = 0.0  # Manual vertical offset for display

        # Data recorder
        self.data_recorder = DataRecorder()

        print("UI Service initialized")

    def start(self, adc_service):
        """Start the UI service"""
        if not self.running:
            self.running = True

            # Initialize PyQt application
            self.app = QApplication([])

            # Import MainWindow here to avoid circular import
            from .ui_main import MainWindow

            # Create main window
            self.window = MainWindow(self, adc_service)
            self.window.show()

            # Start update timer
            self.timer = QTimer()
            self.timer.timeout.connect(self._update_ui)
            self.timer.start(10)  # Update every 10ms for better real-time performance

            # Start recording thread
            self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
            self.recording_thread.start()

            print("UI Service started")

    def stop(self):
        """Stop the UI service"""
        self.running = False
        if self.timer:
            self.timer.stop()
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1.0)
        # Clean queues and buffers
        self.processed_data_queue = queue.Queue(maxsize=30000)
        self.adc_data_queue = queue.Queue(maxsize=30000)
        self.recording_queue = queue.Queue(maxsize=30000)
        self.voltage_buffer.clear()
        self.time_buffer.clear()
        self.sample_count = 0
        self.ecg_record_counter = 0
        self.last_log_time = time.time()
        self.discharge_events.clear()
        self.last_discharge_time = 0
        self.last_r_peak_time = 0
        self.current_lead_index = 0
        self.energia_carga_actual = 0.0
        self.energia_fase1_actual = 0.0
        self.energia_fase2_actual = 0.0
        self.energia_total_ciclo = 0.0
        self.data_recorder.close()
        print("UI Service stopped")

    def run_app(self):
        """Run the Qt application (blocking)"""
        if self.app:
            self.app.exec()

    def add_processed_data(self, processed_data):
        """Add processed signal data to UI"""
        # Non-blocking: drop oldest if full to keep latest data
        try:
            self.processed_data_queue.put_nowait(processed_data)
        except queue.Full:
            # Drop oldest to make room for new
            try:
                self.processed_data_queue.get_nowait()
                self.processed_data_queue.put_nowait(processed_data)
            except queue.Empty:
                pass

    def add_adc_data(self, adc_data):
        """Add ADC data for metadata updates"""
        # Non-blocking: drop oldest if full to keep latest data
        try:
            self.adc_data_queue.put_nowait(adc_data)
        except queue.Full:
            # Drop oldest to make room for new
            try:
                self.adc_data_queue.get_nowait()
                self.adc_data_queue.put_nowait(adc_data)
            except queue.Empty:
                pass

    def update_connection_status(self, esp32_connected: bool, arduino_connected: bool):
        """Update device connection status"""
        self.esp32_connected = esp32_connected
        self.arduino_connected = arduino_connected

    def _recording_worker(self):
        """Background thread for recording data to file"""
        while self.running:
            try:
                record_data = self.recording_queue.get(timeout=0.1)
                # record_data is a tuple: (timestamp, ecg_voltage, vcap, corriente, e_f1, e_f2, e_total, estado)
                self.data_recorder.write_row(*record_data)
                self.recording_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[UI] Recording thread error: {e}")
                time.sleep(0.01)

    def _process_incoming_data(self, max_items_per_update=2000):
        """Process incoming data from queues (limited per update cycle for responsiveness)"""
        items_processed = 0

        # Process processed signal data (limit to prevent UI freezing)
        try:
            while items_processed < max_items_per_update:
                processed_data = self.processed_data_queue.get_nowait()

                # Check for sample count gaps (indicating data loss)
                if self.sample_count > 0 and processed_data.sample_count != self.sample_count + 1:
                    gap = processed_data.sample_count - self.sample_count - 1
                    try:
                        logger.warning(f"Sample count gap detected: expected {self.sample_count + 1}, got {processed_data.sample_count}, gap of {gap} samples")
                    except:
                        pass

                    # Interpolate missing samples
                    if len(self.voltage_buffer) > 0:
                        last_voltage = self.voltage_buffer[-1]
                        current_voltage = processed_data.raw_voltage * self.signal_gain
                        for i in range(1, gap + 1):
                            interpolated_voltage = last_voltage + (current_voltage - last_voltage) * (i / (gap + 1))
                            self.voltage_buffer.append(interpolated_voltage)
                            self.time_buffer.append(self.sample_count + i)

                # Apply gain and offset to raw voltage for display
                voltage_with_gain = processed_data.raw_voltage * self.signal_gain
                voltage_display = voltage_with_gain + self.signal_offset

                # Store in buffers
                self.voltage_buffer.append(voltage_display)
                self.time_buffer.append(processed_data.sample_count)
                self.sample_count = processed_data.sample_count

                # Handle R-peak detection
                if processed_data.peaks:
                    # Peaks are absolute indices in the signal buffer
                    for peak_idx in processed_data.peaks:
                        if peak_idx < len(self.time_buffer):
                            peak_sample = self.time_buffer[peak_idx]
                            peak_timestamp = processed_data.timestamp  # Use the timestamp from processed data
                            self.r_peak_buffer.append(peak_sample)
                            # Update last R-peak time for cardioversor timing
                            self.last_r_peak_time = peak_timestamp

                            # Trigger manual discharge if waiting for R-peak
                            if hasattr(self, 'fire_control') and self.fire_control:
                                self.fire_control.trigger_manual_discharge()

                # Record ECG data at reduced rate (every 10 samples ~100 Hz)
                self.ecg_record_counter += 1
                if self.ecg_record_counter % 10 == 0:
                    # Put in recording queue for background thread
                    try:
                        self.recording_queue.put_nowait((processed_data.timestamp / 1000.0, voltage_with_gain, None, None, None, None, None, None))
                    except queue.Full:
                        pass  # Drop if queue full to avoid blocking

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

                    # Record to CSV via background thread
                    try:
                        self.recording_queue.put_nowait((
                            (energia['timestamp'] if 'timestamp' in energia else adc_data.timestamp) / 1000.0,
                            None,  # ecg_voltage
                            energia['vcap'], energia['corriente'],
                            energia['e_f1'], energia['e_f2'], energia['e_total'], estado
                        ))
                    except queue.Full:
                        pass  # Drop if queue full to avoid blocking

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

        # Periodic logging every 10 seconds
        current_time = time.time()
        if current_time - self.last_log_time > 10:
            try:
                logger.info(f"UI queues - Processed data: {self.processed_data_queue.qsize()}, ADC data: {self.adc_data_queue.qsize()}, Recording: {self.recording_queue.qsize()}")
            except:
                pass
            self.last_log_time = current_time

        # Update plot
        if hasattr(self.window, 'line_raw') and hasattr(self.window, 'r_peak_scatter') and hasattr(self.window, 'status_text') and hasattr(self.window, 'plot_widget'):
            update_plot(self, self.window.plot_widget, self.window.line_raw, self.window.r_peak_scatter, self.window.status_text)

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

        # Calculate BPM from recent R-peaks
        if hasattr(self, 'r_peak_buffer') and len(self.r_peak_buffer) >= 2:
            # Use recent peaks for BPM calculation (last 10 peaks for stability)
            recent_peaks = list(self.r_peak_buffer)[-10:]
            self.current_bpm = calculate_bpm(recent_peaks, SAMPLE_RATE)
        else:
            self.current_bpm = 0.0

        # Update cardioversor status
        if hasattr(self.window, 'cardioversor_status'):
            self.window.cardioversor_status.update_status(
                current_lead=current_lead,
                charge_energy=self.energia_carga_actual,
                phase1_energy=self.energia_fase1_actual,
                phase2_energy=self.energia_fase2_actual,
                total_energy=self.energia_total_ciclo,
                last_discharge_time=last_discharge_time,
                total_discharges=len(self.discharge_events),
                bpm=self.current_bpm
            )

        # Update data recorder status
        if hasattr(self.window, 'data_recorder_control'):
            self.window.data_recorder_control.update_status()