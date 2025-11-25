import threading
from collections import deque
from .filters import BaselineEMA
from .utils import write_csv_row
from .config import buffer_size

class DataManager:
    def __init__(self):
        # Thread-safe variables
        self.data_lock = threading.Lock()
        self.voltage_buffer = deque(maxlen=buffer_size)
        self.filtered_buffer = deque(maxlen=buffer_size)
        self.baseline_buffer = deque(maxlen=buffer_size)
        self.time_buffer = deque(maxlen=buffer_size)
        self.sample_count = 0
        self.esp32_connected = False
        self.arduino_connected = False

        # Buffer para descarga bifásica
        self.descarga_voltage_buffer = deque(maxlen=3000)
        self.descarga_time_buffer = deque(maxlen=3000)
        self.descarga_timestamp_inicio = 0

        # Variables de descargas
        self.discharge_events = []
        self.last_discharge_time = 0
        self.last_r_peak_time = 0

        # Variables de derivación
        self.current_lead_index = 0

        # Variables de energía
        self.energia_carga_actual = 0.0
        self.energia_fase1_actual = 0.0
        self.energia_fase2_actual = 0.0
        self.energia_total_ciclo = 0.0

        # CSV
        self.csv_filename = None
        self.csv_file = None
        self.csv_writer = None
        self.is_recording = True  # Start recording by default

        # Control manual
        self.force_charge = False
        self.force_discharge = False

        # Filter
        self.baseline_filter = BaselineEMA(alpha=0.995)

    def write_csv_row(self, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado):
        if self.is_recording:
            write_csv_row(self.csv_writer, self.csv_file, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado)