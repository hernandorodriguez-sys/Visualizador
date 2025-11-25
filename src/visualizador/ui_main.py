import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PyQt6.QtCore import QTimer, pyqtSlot
from .plot_utils import setup_plot, update_plot, on_lead_di_button, on_lead_dii_button, on_lead_diii_button, on_lead_avr_button
from .data_manager import DataManager
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .utils import init_csv, get_current_lead

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

        # Info text
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(300)
        layout.addWidget(self.info_text)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Update every 50ms

    @pyqtSlot()
    def update_ui(self):
        update_plot(self.data_manager, self.line_raw, self.status_text, self.ax)
        self.canvas.draw()

        # Update info text
        with self.data_manager.data_lock:
            esp32_status = "✓" if self.data_manager.esp32_connected else "✗"
            arduino_status = "✓" if self.data_manager.arduino_connected else "✗"
            current_lead = get_current_lead(self.data_manager.current_lead_index)
            discharge_list = list(self.data_manager.discharge_events)
            ultimo_tiempo_descarga = f"{discharge_list[-1][2]:.0f} ms" if discharge_list else "N/A"

            info = (
                f"╔══════════════╗\n"
                f"║  INFO ECG   ║\n"
                f"╠══════════════╣\n"
                f"║ CONEXIONES   ║\n"
                f"║ ESP32: {esp32_status:>5s}  ║\n"
                f"║ ARD:   {arduino_status:>5s}  ║\n"
                f"╠══════════════╣\n"
                f"║ DERIVACIÓN   ║\n"
                f"║   {current_lead:^4s}       ║\n"
                f"║ (Manual)     ║\n"
                f"╠══════════════╣\n"
                f"║ ENERGÍAS (J) ║\n"
                f"║ Carga:       ║\n"
                f"║  {self.data_manager.energia_carga_actual:>6.2f}      ║\n"
                f"║ Fase 1:      ║\n"
                f"║  {self.data_manager.energia_fase1_actual:>6.3f}      ║\n"
                f"║ Fase 2:      ║\n"
                f"║  {self.data_manager.energia_fase2_actual:>6.3f}      ║\n"
                f"║ Total:       ║\n"
                f"║  {self.data_manager.energia_total_ciclo:>6.3f}      ║\n"
                f"╠══════════════╣\n"
                f"║ ÚLTIMA DESC. ║\n"
                f"║ {ultimo_tiempo_descarga:>9s}  ║\n"
                f"║ (desde R)    ║\n"
                f"╠══════════════╣\n"
                f"║ TOTAL DESC.  ║\n"
                f"║     {len(self.data_manager.discharge_events):>3d}       ║\n"
                f"╚══════════════╝"
            )
            self.info_text.setPlainText(info)

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