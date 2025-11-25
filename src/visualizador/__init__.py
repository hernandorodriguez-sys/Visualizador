"""ECG Monitor Visualizer Package

A real-time ECG monitoring system that reads data from ESP32 and Arduino devices
via serial communication, processes ECG signals, detects R-peaks, and provides
interactive visualization with matplotlib.
"""

__version__ = "0.1.0"

from .config import *
from .data_manager import DataManager
from .filters import BaselineEMA
from .plot_utils import setup_plot, update_plot
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .utils import init_csv, detect_r_peaks_improved

__all__ = [
    "DataManager",
    "BaselineEMA",
    "setup_plot",
    "update_plot",
    "SerialReaderESP32",
    "SerialReaderArduino",
    "init_csv",
    "detect_r_peaks_improved",
]