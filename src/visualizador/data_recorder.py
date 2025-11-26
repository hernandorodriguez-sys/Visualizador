import csv
import os
import time
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
    csv_writer = csv.writer(csv_file, delimiter=';')

    csv_writer.writerow([
        'Timestamp_s',
        'ECG_Voltage_V',
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

def write_csv_row(csv_writer, csv_file, timestamp, ecg_voltage, vcap, corriente, e_f1, e_f2, e_total, estado):
    """Escribe fila en CSV"""
    if csv_writer and csv_file:
        csv_writer.writerow([
            f"{timestamp:.2f}".replace('.', ',') if timestamp is not None else "",
            f"{ecg_voltage:.2f}".replace('.', ',') if ecg_voltage is not None else "",
            f"{vcap:.2f}".replace('.', ',') if vcap is not None else "",
            f"{corriente:.2f}".replace('.', ',') if corriente is not None else "",
            f"{e_f1:.2f}".replace('.', ',') if e_f1 is not None else "",
            f"{e_f2:.2f}".replace('.', ',') if e_f2 is not None else "",
            f"{e_total:.2f}".replace('.', ',') if e_total is not None else "",
            estado if estado is not None else ""
        ])
        csv_file.flush()

class DataRecorder:
    def __init__(self):
        self.csv_filename = None
        self.csv_file = None
        self.csv_writer = None
        self.is_recording = False  # Start recording OFF by default
        self.start_timestamp = None

    def start_recording(self):
        """Start or resume recording"""
        if not self.csv_file:
            self.csv_filename, self.csv_file, self.csv_writer = init_csv()
            self.start_timestamp = time.time() * 1000  # in ms
        self.is_recording = True

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False

    def write_row(self, timestamp, ecg_voltage=None, vcap=None, corriente=None, e_f1=None, e_f2=None, e_total=None, estado=None):
        """Write a row if recording is active"""
        if self.is_recording and self.csv_writer and self.csv_file:
            relative_timestamp = (timestamp - self.start_timestamp / 1000.0) if self.start_timestamp else timestamp
            write_csv_row(self.csv_writer, self.csv_file, relative_timestamp, ecg_voltage, vcap, corriente, e_f1, e_f2, e_total, estado)

    def close(self):
        """Close the CSV file"""
        if self.csv_file:
            self.csv_file.close()
            print(f"Archivo CSV guardado: {self.csv_filename}")