import csv
from datetime import datetime
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
from config import DEBUG_MODE, LEADS, MIN_PEAK_DISTANCE, MIN_PEAK_HEIGHT, PEAK_WIDTH_MIN, PEAK_PROMINENCE, POST_R_DELAY_SAMPLES

def init_csv():
    """Inicializa archivo CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"ecg_data_{timestamp}.csv"

    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)

    csv_writer.writerow([
        'Timestamp_ms',
        'Voltaje_Capacitor_V',
        'Corriente_A',
        'Energia_Fase1_J',
        'Energia_Fase2_J',
        'Energia_Total_J',
        'Estado'
    ])
    csv_file.flush()

    print(f"Archivo CSV creado: {csv_filename}")
    return csv_filename, csv_file, csv_writer

def write_csv_row(csv_writer, csv_file, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado):
    """Escribe fila en CSV"""
    if csv_writer:
        csv_writer.writerow([
            timestamp,
            f"{vcap:.3f}",
            f"{corriente:.3f}",
            f"{e_f1:.4f}",
            f"{e_f2:.4f}",
            f"{e_total:.4f}",
            estado
        ])
        csv_file.flush()

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