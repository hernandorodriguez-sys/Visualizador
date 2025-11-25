import threading
from collections import deque
from .filters import BaselineEMA
from .data_recorder import DataRecorder
from .config import buffer_size

class DataManager:
    def __init__(self):
        # Thread-safe variables
        self.data_lock = threading.Lock()
        self.voltage_buffer = deque(maxlen=buffer_size)
        self.filtered_buffer = deque(maxlen=buffer_size)
        self.antialiased_buffer = deque(maxlen=buffer_size)
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

        # Data Recorder
        self.data_recorder = DataRecorder()

        # Control manual
        self.force_charge = False
        self.force_discharge = False

        # Filter
        self.baseline_filter = BaselineEMA(alpha=0.995)

        # Plot settings
        self.plot_y_min = -0.5
        self.plot_y_max = 4.0  # Limited to 4V as requested
        self.plot_window_size = 1500
        self.plot_time_axis = False  # False = samples, True = time
        self.signal_gain = 1.0  # Signal gain multiplier

    def write_csv_row(self, timestamp, vcap, corriente, e_f1, e_f2, e_total, estado):
        self.data_recorder.write_row(timestamp, vcap, corriente, e_f1, e_f2, e_total, estado)