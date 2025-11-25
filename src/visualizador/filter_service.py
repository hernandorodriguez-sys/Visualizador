import threading
import time
from .filters import IIRAntiAlias
from .config import SAMPLE_RATE

class RealTimeFilterService:
    """Threaded service for real-time signal filtering"""

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.running = False
        self.thread = None

        # IIR Anti-aliasing filter
        self.iir_filter = IIRAntiAlias(sample_rate=SAMPLE_RATE, cutoff_freq=400, order=4)

        # Track last processed sample
        self.last_processed_index = 0

        print("Servicio de filtrado en tiempo real inicializado")

    def process_new_samples(self):
        """Process any new samples that have arrived"""
        with self.data_manager.data_lock:
            current_length = len(self.data_manager.voltage_buffer)

            # Process samples from last_processed_index to current_length
            for i in range(self.last_processed_index, current_length):
                voltage = self.data_manager.voltage_buffer[i]
                antialiased = self.iir_filter.process_sample(voltage)
                self.data_manager.antialiased_buffer.append(antialiased)

            self.last_processed_index = current_length

    def run(self):
        """Main service loop"""
        print("Servicio de filtrado en tiempo real ejecutándose...")

        while self.running:
            try:
                self.process_new_samples()
                time.sleep(0.001)  # Small delay to prevent busy waiting
            except Exception as e:
                print(f"Error en servicio de filtrado: {e}")
                time.sleep(0.1)

        print("Servicio de filtrado detenido")

    def start(self):
        """Start the filtering service thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("Servicio de filtrado en tiempo real iniciado")

    def stop(self):
        """Stop the filtering service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("Servicio de filtrado en tiempo real detenido")