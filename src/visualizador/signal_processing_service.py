import threading
import queue
import time
import logging
from collections import deque
import numpy as np
from scipy import signal
from typing import NamedTuple, Optional
from .config import SAMPLE_RATE, MIN_PEAK_HEIGHT, MIN_PEAK_DISTANCE, PEAK_WIDTH_MIN, PEAK_PROMINENCE
from .data_types import ADCData

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessedData(NamedTuple):
    """Data structure for processed signal data"""
    timestamp: int
    raw_voltage: float
    filtered_voltage: float
    sample_count: int
    peaks: list = None  # List of peak indices
    metadata: dict = None

class SignalProcessingService:
    """Service responsible for real-time signal processing and filtering"""

    def __init__(self):
        self.running = False
        self.thread = None

        # Communication queues
        self.input_queue = queue.Queue(maxsize=15000)  # Raw ADC data input
        self.output_queue = queue.Queue(maxsize=15000)  # Processed data output

        # Service references
        self.ui_service = None

        # Processing buffers
        self.signal_buffer = deque(maxlen=1000)  # Keep last 1000 samples for peak detection
        self.buffer_size = 1000  # Size for filtering window
        self.sample_count = 0
        self.last_log_time = time.time()

        # Filter parameters
        self.nyquist = SAMPLE_RATE / 2
        # Configurable bandpass filter: default 0.05 - 50 Hz
        self.low_cutoff = 0.05
        self.high_cutoff = 50.0

        # Design FIR bandpass filter for stability
        self.fir_coeffs = signal.firwin(101, [self.low_cutoff/self.nyquist, self.high_cutoff/self.nyquist], pass_zero=False)
        self.filter_state = np.zeros(len(self.fir_coeffs) - 1)

        print("Signal Processing Service initialized")

    def update_filter_parameters(self, low_cutoff: float, high_cutoff: float):
        """Update the bandpass filter parameters and redesign the filter"""
        if low_cutoff >= high_cutoff or low_cutoff < 0.05 or high_cutoff > 120.0 or high_cutoff >= self.nyquist:
            print(f"Invalid filter parameters: low={low_cutoff}, high={high_cutoff}")
            return False

        self.low_cutoff = low_cutoff
        self.high_cutoff = high_cutoff

        # Redesign FIR bandpass filter
        self.fir_coeffs = signal.firwin(101, [self.low_cutoff/self.nyquist, self.high_cutoff/self.nyquist], pass_zero=False)
        self.filter_state = np.zeros(len(self.fir_coeffs) - 1)

        print(f"Filter updated: {self.low_cutoff:.3f} - {self.high_cutoff:.3f} Hz")
        return True

    def set_ui_service(self, ui_service):
        """Set the UI service to send processed data to"""
        self.ui_service = ui_service

    def start(self):
        """Start the signal processing service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.thread.start()
            print("Signal Processing Service started")

    def stop(self):
        """Stop the signal processing service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        # Clean queues and buffers
        self.input_queue = queue.Queue(maxsize=15000)
        self.output_queue = queue.Queue(maxsize=15000)
        self.signal_buffer.clear()
        self.sample_count = 0
        self.last_log_time = time.time()
        print("Signal Processing Service stopped")

    def process_data(self, adc_data: ADCData):
        """Add raw ADC data for processing"""
        # Non-blocking: drop oldest if full to keep latest data
        try:
            self.input_queue.put_nowait(adc_data)
        except queue.Full:
            # Drop oldest to make room for new
            try:
                self.input_queue.get_nowait()
                self.input_queue.put_nowait(adc_data)
            except queue.Empty:
                pass

    def get_processed_data(self, timeout: float = 0.1) -> Optional[ProcessedData]:
        """Get next processed data from queue"""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _apply_filter(self, voltage: float) -> float:
        """Apply real-time FIR bandpass filter to voltage"""
        # Apply FIR filter using maintained state
        filtered, self.filter_state = signal.lfilter(self.fir_coeffs, 1.0, [voltage], zi=self.filter_state)
        # FIR filters are always stable, but clamp anyway for safety
        clamped = max(-5.0, min(5.0, filtered[0]))
        return clamped

    def _detect_peaks(self, filtered_signal) -> list:
        """Detect peaks in the filtered signal"""
        if len(filtered_signal) < MIN_PEAK_DISTANCE:
            return []

        # Convert to numpy array
        signal_array = np.array(list(filtered_signal))

        # Find peaks
        peaks, _ = signal.find_peaks(
            signal_array,
            height=MIN_PEAK_HEIGHT,
            distance=MIN_PEAK_DISTANCE,
            width=PEAK_WIDTH_MIN,
            prominence=PEAK_PROMINENCE
        )

        return peaks.tolist()

    def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Get raw data from input queue
                adc_data = self.input_queue.get(timeout=0.1)

                # Apply filtering
                filtered_voltage = self._apply_filter(adc_data.voltage)

                # Add to signal buffer for peak detection
                self.signal_buffer.append(filtered_voltage)

                # Periodically reset filter state to prevent drift
                if self.sample_count % 10000 == 0:  # Reset every 10000 samples
                    self.filter_state = np.zeros(len(self.fir_coeffs) - 1)

                # Detect peaks periodically (every 500 samples to avoid overhead)
                peaks = []
                if self.sample_count % 500 == 0 and len(self.signal_buffer) >= MIN_PEAK_DISTANCE:
                    peaks = self._detect_peaks(list(self.signal_buffer)[-200:])  # Check last 200 samples

                # Create processed data
                processed = ProcessedData(
                    timestamp=adc_data.timestamp,
                    raw_voltage=adc_data.voltage,
                    filtered_voltage=filtered_voltage,
                    sample_count=self.sample_count,
                    peaks=peaks if peaks else None,
                    metadata=adc_data.metadata
                )

                # Send processed data to UI service
                if self.ui_service:
                    # Convert to UI service format - send raw voltage so gain control works
                    from .ui_service import ProcessedData as UIProcessedData
                    ui_processed = UIProcessedData(
                        timestamp=processed.timestamp,
                        raw_voltage=processed.filtered_voltage,  # Send filtered voltage for display
                        sample_count=processed.sample_count,
                        metadata=processed.metadata
                    )
                    self.ui_service.add_processed_data(ui_processed)

                # Send to output queue (for external access if needed)
                # Non-blocking: drop oldest if full
                try:
                    self.output_queue.put_nowait(processed)
                except queue.Full:
                    try:
                        self.output_queue.get_nowait()
                        self.output_queue.put_nowait(processed)
                    except queue.Empty:
                        pass

                self.sample_count += 1
                self.input_queue.task_done()

                # Periodic logging every 10 seconds
                current_time = time.time()
                if current_time - self.last_log_time > 10:
                    try:
                        logger.info(f"Signal processing queues - Input: {self.input_queue.qsize()}, Output: {self.output_queue.qsize()}")
                    except:
                        pass
                    self.last_log_time = current_time

            except queue.Empty:
                continue
            except Exception as e:
                try:
                    logger.error(f"Signal processing error: {e}", exc_info=True)
                except:
                    pass
                time.sleep(0.01)