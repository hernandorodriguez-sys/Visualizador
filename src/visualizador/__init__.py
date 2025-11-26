"""ECG Monitor Visualizer Package

A real-time ECG monitoring system that reads data from ESP32 and Arduino devices
via serial communication, processes ECG signals, detects R-peaks, and provides
interactive visualization with matplotlib.
"""

__version__ = "0.1.0"

from .config import *
from .data_manager import DataManager
from .plot_utils import setup_plot, update_plot
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .data_recorder import DataRecorder

__all__ = [
    "DataManager",
    "setup_plot",
    "update_plot",
    "SerialReaderESP32",
    "SerialReaderArduino",
    "DataRecorder",
]