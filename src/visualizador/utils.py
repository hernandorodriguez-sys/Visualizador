import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
from .config import DEBUG_MODE, LEADS, MIN_PEAK_DISTANCE, MIN_PEAK_HEIGHT, PEAK_WIDTH_MIN, PEAK_PROMINENCE, POST_R_DELAY_SAMPLES

def get_current_lead(current_lead_index):
    """Obtiene derivación actual"""
    return LEADS[current_lead_index] if current_lead_index < len(LEADS) else "??"

def detect_r_peaks_improved(signal_data):
    """Detecta picos R en la señal usando método robusto"""
    if len(signal_data) < MIN_PEAK_DISTANCE * 2:
        return []

    signal_array = np.array(signal_data)

    smoothed = gaussian_filter1d(signal_array, sigma=1.5)

    signal_std = np.std(smoothed)
    signal_mean = np.mean(smoothed)

    dynamic_threshold = signal_mean + 0.8 * signal_std
    dynamic_threshold = max(MIN_PEAK_HEIGHT, dynamic_threshold)

    try:
        peaks, properties = signal.find_peaks(
            smoothed,
            height=dynamic_threshold,
            distance=MIN_PEAK_DISTANCE,
            width=PEAK_WIDTH_MIN,
            prominence=PEAK_PROMINENCE
        )

        validated_peaks = []
        for peak in peaks:
            start_idx = max(0, peak - 8)
            end_idx = min(len(smoothed), peak + 9)
            local_window = smoothed[start_idx:end_idx]

            local_max_idx = np.argmax(local_window)
            if abs(local_max_idx - (peak - start_idx)) <= 2:
                validated_peaks.append(peak)

        return validated_peaks

    except Exception as e:
        if DEBUG_MODE:
            print(f"Error en detección de picos: {e}")
        return []

def calculate_post_r_markers(r_peaks_indices):
    """Calcula marcadores 20ms después de picos R"""
    post_r_markers = []
    for peak_idx in r_peaks_indices:
        post_r_idx = peak_idx + POST_R_DELAY_SAMPLES
        post_r_markers.append(post_r_idx)
    return post_r_markers