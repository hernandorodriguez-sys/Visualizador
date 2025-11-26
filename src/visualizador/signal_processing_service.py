import threading
import queue
import time
import numpy as np
from scipy import signal
from typing import NamedTuple, Optional
from .config import SAMPLE_RATE, MIN_PEAK_HEIGHT, MIN_PEAK_DISTANCE, PEAK_WIDTH_MIN, PEAK_PROMINENCE
from .data_types import ADCData

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
        self.input_queue = queue.Queue(maxsize=10000)  # Raw ADC data input
        self.output_queue = queue.Queue(maxsize=10000)  # Processed data output

        # Service references
        self.ui_service = None

        # Processing buffers
        self.signal_buffer = []
        self.buffer_size = 1000  # Size for filtering window
        self.sample_count = 0

        # Filter parameters
        self.nyquist = SAMPLE_RATE / 2
        # ECG bandpass filter: 0.5 - 40 Hz
        self.low_cutoff = 0.5
        self.high_cutoff = 40.0

        # Design FIR bandpass filter for stability
        self.fir_coeffs = signal.firwin(101, [self.low_cutoff/self.nyquist, self.high_cutoff/self.nyquist], pass_zero=False)
        self.filter_state = np.zeros(len(self.fir_coeffs) - 1)

        print("Signal Processing Service initialized")

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
        print("Signal Processing Service stopped")

    def process_data(self, adc_data: ADCData):
        """Add raw ADC data for processing"""
        try:
            self.input_queue.put_nowait(adc_data)
        except queue.Full:
            # Remove oldest data if queue is full
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

    def _detect_peaks(self, filtered_signal: list) -> list:
        """Detect peaks in the filtered signal"""
        if len(filtered_signal) < MIN_PEAK_DISTANCE:
            return []

        # Convert to numpy array
        signal_array = np.array(filtered_signal)

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

                # Periodically reset filter state to prevent drift
                if self.sample_count % 10000 == 0:  # Reset every 10000 samples
                    self.filter_state = np.zeros(len(self.fir_coeffs) - 1)

                # Detect peaks periodically (every 100 samples to avoid overhead)
                peaks = []
                if self.sample_count % 100 == 0 and len(self.signal_buffer) >= MIN_PEAK_DISTANCE:
                    peaks = self._detect_peaks(self.signal_buffer[-200:])  # Check last 200 samples

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
                try:
                    self.output_queue.put_nowait(processed)
                except queue.Full:
                    # Remove oldest if full
                    try:
                        self.output_queue.get_nowait()
                        self.output_queue.put_nowait(processed)
                    except queue.Empty:
                        pass

                self.sample_count += 1
                self.input_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Signal processing error: {e}")
                time.sleep(0.01)