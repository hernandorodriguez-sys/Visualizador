"""
Functions for R-peak detection in ECG signals.
"""
import numpy as np
from scipy import signal

def detect_r_peaks(signal_data, threshold, distance):
    """
    Detects R-peaks in a signal using scipy's find_peaks with height and prominence.

    Args:
        signal_data (list or np.array): The ECG signal.
        threshold (float): The minimum height for a peak.
        distance (int): The minimum number of samples between peaks.

    Returns:
        list: A list of indices where R-peaks are detected.
    """
    if len(signal_data) < 3:
        return []

    # Use scipy find_peaks with height and distance
    # Prominence helps detect significant peaks
    prominence = threshold * 0.5  # Prominence at least half the threshold
    peaks, _ = signal.find_peaks(signal_data, height=threshold, distance=distance, prominence=prominence)

    return peaks.tolist()

def calculate_bpm(peaks, sample_rate):
    """
    Calculates Beats Per Minute (BPM) from a list of peak indices.

    Args:
        peaks (list): Indices of the detected peaks.
        sample_rate (int): The sampling rate of the signal in Hz.

    Returns:
        float: The calculated BPM, or 0 if not enough peaks are found.
    """
    if len(peaks) < 2:
        return 0

    avg_interval = np.mean(np.diff(peaks))
    if avg_interval > 0:
        bpm = 60 / (avg_interval / sample_rate)
        return bpm

    return 0