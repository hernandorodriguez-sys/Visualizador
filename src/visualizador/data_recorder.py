import csv
import os
from datetime import datetime

RECORDINGS_DIR = "recordings"

def ensure_recordings_dir():
    """Ensure recordings directory exists"""
    if not os.path.exists(RECORDINGS_DIR):
        os.makedirs(RECORDINGS_DIR)

def init_csv():
    """Inicializa archivo CSV"""
    ensure_recordings_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join(RECORDINGS_DIR, f"ecg_data_{timestamp}.csv")

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
    if csv_writer and csv_file:
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

class DataRecorder:
    def __init__(self):
        self.csv_filename = None
        self.csv_file = None
        self.csv_writer = None
        self.is_recording = True  # Start recording by default

    def start_recording(self):
        """Start or resume recording"""
        if not self.csv_file:
            self.csv_filename, self.csv_file, self.csv_writer = init_csv()
        self.is_recording = True

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False

    def write_row(self, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado):
        """Write a row if recording is active"""
        if self.is_recording and self.csv_writer and self.csv_file:
            write_csv_row(self.csv_writer, self.csv_file, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado)

    def close(self):
        """Close the CSV file"""
        if self.csv_file:
            self.csv_file.close()
            print(f"Archivo CSV guardado: {self.csv_filename}")