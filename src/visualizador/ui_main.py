import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import QTimer, pyqtSlot
from .plot_utils import setup_plot, update_plot, on_lead_di_button, on_lead_dii_button, on_lead_diii_button, on_lead_avr_button
from .data_manager import DataManager
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .utils import init_csv, get_current_lead

class InfoPanel(QGroupBox):
    def __init__(self):
        super().__init__("ECG Information")
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Connection status
        layout.addWidget(QLabel("Connections:"), 0, 0)
        self.esp32_status = QLabel("ESP32: Disconnected")
        layout.addWidget(self.esp32_status, 0, 1)
        self.arduino_status = QLabel("Arduino: Disconnected")
        layout.addWidget(self.arduino_status, 0, 2)

        # Current lead
        layout.addWidget(QLabel("Current Lead:"), 1, 0)
        self.current_lead = QLabel("None")
        layout.addWidget(self.current_lead, 1, 1, 1, 2)

        # Energies
        layout.addWidget(QLabel("Energies (J):"), 2, 0)
        layout.addWidget(QLabel("Charge:"), 3, 0)
        self.charge_energy = QLabel("0.000")
        layout.addWidget(self.charge_energy, 3, 1)
        layout.addWidget(QLabel("Phase 1:"), 4, 0)
        self.phase1_energy = QLabel("0.000")
        layout.addWidget(self.phase1_energy, 4, 1)
        layout.addWidget(QLabel("Phase 2:"), 5, 0)
        self.phase2_energy = QLabel("0.000")
        layout.addWidget(self.phase2_energy, 5, 1)
        layout.addWidget(QLabel("Total:"), 6, 0)
        self.total_energy = QLabel("0.000")
        layout.addWidget(self.total_energy, 6, 1)

        # Discharge info
        layout.addWidget(QLabel("Last Discharge:"), 2, 2)
        self.last_discharge_time = QLabel("N/A")
        layout.addWidget(self.last_discharge_time, 3, 2)
        layout.addWidget(QLabel("Total Discharges:"), 4, 2)
        self.total_discharges = QLabel("0")
        layout.addWidget(self.total_discharges, 5, 2)

        self.setLayout(layout)

    def update_info(self, esp32_connected, arduino_connected, current_lead,
                   charge_energy, phase1_energy, phase2_energy, total_energy,
                   last_discharge_time, total_discharges):
        self.esp32_status.setText(f"ESP32: {'Connected' if esp32_connected else 'Disconnected'}")
        self.arduino_status.setText(f"Arduino: {'Connected' if arduino_connected else 'Disconnected'}")
        self.current_lead.setText(current_lead)
        self.charge_energy.setText(f"{charge_energy:.3f}")
        self.phase1_energy.setText(f"{phase1_energy:.3f}")
        self.phase2_energy.setText(f"{phase2_energy:.3f}")
        self.total_energy.setText(f"{total_energy:.3f}")
        self.last_discharge_time.setText(last_discharge_time)
        self.total_discharges.setText(str(total_discharges))

class MainWindow(QMainWindow):
    def __init__(self, data_manager, serial_reader_esp32, serial_reader_arduino):
        super().__init__()
        self.data_manager = data_manager
        self.serial_reader_esp32 = serial_reader_esp32
        self.serial_reader_arduino = serial_reader_arduino

        self.setWindowTitle("Monitor ECG - ADC Raw")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # Matplotlib canvas
        self.canvas, self.ax, self.line_raw, self.status_text = setup_plot()
        layout.addWidget(self.canvas)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.btn_di = QPushButton('DI')
        self.btn_di.clicked.connect(lambda: self.on_lead_button('DI'))
        buttons_layout.addWidget(self.btn_di)

        self.btn_dii = QPushButton('DII')
        self.btn_dii.clicked.connect(lambda: self.on_lead_button('DII'))
        buttons_layout.addWidget(self.btn_dii)

        self.btn_diii = QPushButton('DIII')
        self.btn_diii.clicked.connect(lambda: self.on_lead_button('DIII'))
        buttons_layout.addWidget(self.btn_diii)

        self.btn_avr = QPushButton('aVR')
        self.btn_avr.clicked.connect(lambda: self.on_lead_button('aVR'))
        buttons_layout.addWidget(self.btn_avr)

        layout.addLayout(buttons_layout)

        # Info panel
        self.info_panel = InfoPanel()
        layout.addWidget(self.info_panel)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Update every 50ms

    @pyqtSlot()
    def update_ui(self):
        update_plot(self.data_manager, self.line_raw, self.status_text, self.ax)
        self.canvas.draw()

        # Update info panel
        with self.data_manager.data_lock:
            current_lead = get_current_lead(self.data_manager.current_lead_index)
            discharge_list = list(self.data_manager.discharge_events)
            last_discharge_time = f"{discharge_list[-1][2]:.0f} ms" if discharge_list else "N/A"

            self.info_panel.update_info(
                esp32_connected=self.data_manager.esp32_connected,
                arduino_connected=self.data_manager.arduino_connected,
                current_lead=current_lead,
                charge_energy=self.data_manager.energia_carga_actual,
                phase1_energy=self.data_manager.energia_fase1_actual,
                phase2_energy=self.data_manager.energia_fase2_actual,
                total_energy=self.data_manager.energia_total_ciclo,
                last_discharge_time=last_discharge_time,
                total_discharges=len(self.data_manager.discharge_events)
            )

    def on_lead_button(self, lead):
        if lead == 'DI':
            on_lead_di_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'DII':
            on_lead_dii_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'DIII':
            on_lead_diii_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'aVR':
            on_lead_avr_button(None, self.data_manager, self.serial_reader_esp32)

    def closeEvent(self, event):
        self.timer.stop()
        self.serial_reader_esp32.stop()
        self.serial_reader_arduino.stop()
        if self.data_manager.csv_file:
            self.data_manager.csv_file.close()
        event.accept()