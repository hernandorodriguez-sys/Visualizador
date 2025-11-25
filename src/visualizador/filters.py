# Filters module for ECG signal processing
import numpy as np
from scipy import signal

class BaselineEMA:
    """Filtro minimalista: solo EMA baseline para eliminar drift."""
    def __init__(self, alpha=0.995):
        self.alpha = alpha
        self.baseline = None
        print(f"Filtro Baseline EMA configurado (alpha={alpha})")

    def process_sample(self, voltage):
        if self.baseline is None:
            self.baseline = voltage
        else:
            self.baseline = self.alpha * self.baseline + (1.0 - self.alpha) * voltage

        filtered = voltage - self.baseline
        return filtered, self.baseline

class IIRAntiAlias:
    """IIR Butterworth low-pass filter for anti-aliasing"""
    def __init__(self, sample_rate=2000, cutoff_freq=400, order=4):
        self.sample_rate = sample_rate
        self.cutoff_freq = cutoff_freq
        self.order = order

        # Design Butterworth filter
        nyquist = sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        self.b, self.a = signal.butter(order, normalized_cutoff, btype='low')

        # Initialize filter state
        self.zi = signal.lfilter_zi(self.b, self.a)

        print(f"Filtro IIR Anti-Aliasing configurado (corte={cutoff_freq}Hz, orden={order})")

    def process_sample(self, voltage):
        """Process a single sample through the IIR filter"""
        filtered, self.zi = signal.lfilter(self.b, self.a, [voltage], zi=self.zi)
        return filtered[0]

    def reset(self):
        """Reset filter state"""
        self.zi = signal.lfilter_zi(self.b, self.a)