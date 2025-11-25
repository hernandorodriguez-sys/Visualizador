# Filters module for ECG signal processing

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