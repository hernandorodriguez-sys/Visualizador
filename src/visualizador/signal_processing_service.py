import threading
import queue
import time
from typing import NamedTuple, Optional
from .filters import IIRAntiAlias, BaselineEMA
from .config import SAMPLE_RATE

class ProcessedData(NamedTuple):
    """Data structure for processed signal data"""
    timestamp: int
    raw_voltage: float
    filtered_voltage: float
    baseline: float
    antialiased_voltage: float
    sample_count: int
    metadata: dict = None

class SignalProcessingService:
    """Service responsible for signal processing (filtering)"""

    def __init__(self):
        self.running = False
        self.thread = None

        # Communication queues
        self.input_queue = queue.Queue(maxsize=10000)  # Raw ADC data input
        self.output_queue = queue.Queue(maxsize=10000)  # Processed data output

        # Filters
        self.baseline_filter = BaselineEMA(alpha=0.995)
        self.iir_filter = IIRAntiAlias(sample_rate=SAMPLE_RATE, cutoff_freq=400, order=4)

        # Processing state
        self.sample_count = 0
        self.last_processed_timestamp = 0

        # Service reference
        self.ui_service = None

        print("Signal Processing Service initialized")

    def set_ui_service(self, ui_service):
        """Set reference to UI service"""
        self.ui_service = ui_service

    def start(self):
        """Start the signal processing service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("Signal Processing Service started")

    def stop(self):
        """Stop the signal processing service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("Signal Processing Service stopped")

    def process_data(self, adc_data):
        """Add ADC data to processing queue"""
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

    def _run(self):
        """Main processing loop"""
        while self.running:
            try:
                # Process up to 1000 items per cycle for real-time performance
                items_processed = 0
                max_items_per_cycle = 1000

                while items_processed < max_items_per_cycle:
                    try:
                        # Get raw ADC data
                        adc_data = self.input_queue.get(timeout=0.001)
                        if adc_data.source == 'esp32':  # Process all ESP32 data
                            # Apply baseline filter
                            filtered_voltage, baseline = self.baseline_filter.process_sample(adc_data.voltage)

                            # Apply anti-aliasing filter
                            antialiased_voltage = self.iir_filter.process_sample(filtered_voltage)

                            # Create processed data
                            processed = ProcessedData(
                                timestamp=adc_data.timestamp,
                                raw_voltage=adc_data.voltage,
                                filtered_voltage=filtered_voltage,
                                baseline=baseline,
                                antialiased_voltage=antialiased_voltage,
                                sample_count=self.sample_count,
                                metadata=adc_data.metadata
                            )

                            # Send to UI service
                            if self.ui_service:
                                self.ui_service.add_processed_data(processed)

                            # Send to output queue
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
                        items_processed += 1

                    except queue.Empty:
                        break  # No more data to process

                # Small delay if we processed the maximum
                if items_processed >= max_items_per_cycle:
                    time.sleep(0.001)
                else:
                    time.sleep(0.0001)  # Very small delay when idle

            except Exception as e:
                print(f"Signal Processing error: {e}")
                time.sleep(0.01)