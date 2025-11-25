import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QGroupBox, QGridLayout, QMessageBox, QSlider, QCheckBox, QSpinBox
from PyQt6.QtCore import QTimer, pyqtSlot, Qt
from .plot_utils import setup_plot, update_plot, on_lead_di_button, on_lead_dii_button, on_lead_diii_button, on_lead_avr_button
from .data_manager import DataManager
from .serial_readers import SerialReaderESP32, SerialReaderArduino
from .utils import get_current_lead

class DeviceStatusWidget(QGroupBox):
    def __init__(self):
        super().__init__("Device Status")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.esp32_status = QLabel("ESP32: Disconnected")
        self.esp32_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.esp32_status)

        self.arduino_status = QLabel("Arduino: Disconnected")
        self.arduino_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.arduino_status)

        layout.addStretch()
        self.setLayout(layout)

    def update_status(self, esp32_connected, arduino_connected):
        if esp32_connected:
            self.esp32_status.setText("ESP32: Connected")
            self.esp32_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.esp32_status.setText("ESP32: Disconnected")
            self.esp32_status.setStyleSheet("color: red; font-weight: bold;")

        if arduino_connected:
            self.arduino_status.setText("Arduino: Connected")
            self.arduino_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.arduino_status.setText("Arduino: Disconnected")
            self.arduino_status.setStyleSheet("color: red; font-weight: bold;")


class CardioversorStatusWidget(QGroupBox):
    def __init__(self):
        super().__init__("Cardioversor Status")
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Current lead
        layout.addWidget(QLabel("Current Lead:"), 0, 0)
        self.current_lead = QLabel("None")
        self.current_lead.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.current_lead, 0, 1)

        # Energies
        layout.addWidget(QLabel("Energies (J):"), 1, 0)
        layout.addWidget(QLabel("Charge:"), 2, 0)
        self.charge_energy = QLabel("0.000")
        layout.addWidget(self.charge_energy, 2, 1)
        layout.addWidget(QLabel("Phase 1:"), 3, 0)
        self.phase1_energy = QLabel("0.000")
        layout.addWidget(self.phase1_energy, 3, 1)
        layout.addWidget(QLabel("Phase 2:"), 4, 0)
        self.phase2_energy = QLabel("0.000")
        layout.addWidget(self.phase2_energy, 4, 1)
        layout.addWidget(QLabel("Total:"), 5, 0)
        self.total_energy = QLabel("0.000")
        self.total_energy.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.total_energy, 5, 1)

        # Discharge info
        layout.addWidget(QLabel("Last Discharge:"), 1, 2)
        self.last_discharge_time = QLabel("N/A")
        layout.addWidget(self.last_discharge_time, 2, 2)
        layout.addWidget(QLabel("Total Discharges:"), 3, 2)
        self.total_discharges = QLabel("0")
        layout.addWidget(self.total_discharges, 4, 2)

        self.setLayout(layout)

    def update_status(self, current_lead, charge_energy, phase1_energy, phase2_energy,
                     total_energy, last_discharge_time, total_discharges):
        self.current_lead.setText(current_lead)
        self.charge_energy.setText(f"{charge_energy:.3f}")
        self.phase1_energy.setText(f"{phase1_energy:.3f}")
        self.phase2_energy.setText(f"{phase2_energy:.3f}")
        self.total_energy.setText(f"{total_energy:.3f}")
        self.last_discharge_time.setText(last_discharge_time)
        self.total_discharges.setText(str(total_discharges))


class CardioversorControlWidget(QGroupBox):
    def __init__(self, serial_reader_arduino):
        super().__init__("Cardioversor Control")
        self.serial_reader_arduino = serial_reader_arduino
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.armar_button = QPushButton("ARMAR")
        self.armar_button.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
        self.armar_button.clicked.connect(self.on_armar_clicked)
        layout.addWidget(self.armar_button)

        self.desarmar_button = QPushButton("Desarmar")
        self.desarmar_button.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
        self.desarmar_button.clicked.connect(self.on_desarmar_clicked)
        layout.addWidget(self.desarmar_button)

        self.setLayout(layout)

    def on_armar_clicked(self):
        reply = QMessageBox.question(
            self, 'Confirmar ARMAR',
            "¿Está seguro de que desea ARMAR el cardioversor?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.serial_reader_arduino.send_command("ARM")

    def on_desarmar_clicked(self):
        self.serial_reader_arduino.send_command("DISARM")


class CardioversorFireControlWidget(QGroupBox):
    def __init__(self, serial_reader_arduino):
        super().__init__("Fire Control")
        self.serial_reader_arduino = serial_reader_arduino
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.auto_button = QPushButton("Auto")
        self.auto_button.clicked.connect(self.on_auto_clicked)
        layout.addWidget(self.auto_button)

        self.manual_button = QPushButton("Manual")
        self.manual_button.clicked.connect(self.on_manual_clicked)
        layout.addWidget(self.manual_button)

        self.test_fire_button = QPushButton("Test Fire")
        self.test_fire_button.setStyleSheet("background-color: orange; color: white; font-weight: bold;")
        self.test_fire_button.clicked.connect(self.on_test_fire_clicked)
        layout.addWidget(self.test_fire_button)

        self.setLayout(layout)

    def on_auto_clicked(self):
        self.serial_reader_arduino.send_command("AUTO")

    def on_manual_clicked(self):
        self.serial_reader_arduino.send_command("MANUAL")

    def on_test_fire_clicked(self):
        reply = QMessageBox.question(
            self, 'Confirmar Test Fire',
            "¿Está seguro de que desea realizar Test Fire?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.serial_reader_arduino.send_command("TEST_FIRE")


class LeadControlWidget(QGroupBox):
    def __init__(self, data_manager, serial_reader_esp32):
        super().__init__("Control Derivada")
        self.data_manager = data_manager
        self.serial_reader_esp32 = serial_reader_esp32
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.btn_di = QPushButton('DI')
        self.btn_di.clicked.connect(lambda: self.on_lead_button('DI'))
        layout.addWidget(self.btn_di)

        self.btn_dii = QPushButton('DII')
        self.btn_dii.clicked.connect(lambda: self.on_lead_button('DII'))
        layout.addWidget(self.btn_dii)

        self.btn_diii = QPushButton('DIII')
        self.btn_diii.clicked.connect(lambda: self.on_lead_button('DIII'))
        layout.addWidget(self.btn_diii)

        self.btn_avr = QPushButton('aVR')
        self.btn_avr.clicked.connect(lambda: self.on_lead_button('aVR'))
        layout.addWidget(self.btn_avr)

        self.setLayout(layout)

    def on_lead_button(self, lead):
        if lead == 'DI':
            on_lead_di_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'DII':
            on_lead_dii_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'DIII':
            on_lead_diii_button(None, self.data_manager, self.serial_reader_esp32)
        elif lead == 'aVR':
            on_lead_avr_button(None, self.data_manager, self.serial_reader_esp32)


class DataRecorderControlWidget(QGroupBox):
    def __init__(self, data_manager):
        super().__init__("Data Recorder")
        self.data_manager = data_manager
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.start_button = QPushButton("Start Recording")
        self.start_button.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 5px;")
        self.start_button.clicked.connect(self.on_start_clicked)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 5px;")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        layout.addWidget(self.stop_button)

        self.status_label = QLabel("Recording: ON")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def on_start_clicked(self):
        with self.data_manager.data_lock:
            self.data_manager.data_recorder.start_recording()
        self.update_status()

    def on_stop_clicked(self):
        with self.data_manager.data_lock:
            self.data_manager.data_recorder.stop_recording()
        self.update_status()

    def update_status(self):
        with self.data_manager.data_lock:
            is_recording = self.data_manager.data_recorder.is_recording
        if is_recording:
            self.status_label.setText("Recording: ON")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.status_label.setText("Recording: OFF")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")


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
        self.canvas, self.ax, self.line_raw, self.status_text = setup_plot(self.data_manager)
        layout.addWidget(self.canvas)

        # Status panels
        status_layout = QHBoxLayout()
        self.device_status = DeviceStatusWidget()
        status_layout.addWidget(self.device_status)
        self.cardioversor_status = CardioversorStatusWidget()
        status_layout.addWidget(self.cardioversor_status)
        self.cardioversor_control = CardioversorControlWidget(self.serial_reader_arduino)
        status_layout.addWidget(self.cardioversor_control)
        self.fire_control = CardioversorFireControlWidget(self.serial_reader_arduino)
        status_layout.addWidget(self.fire_control)
        self.lead_control = LeadControlWidget(self.data_manager, self.serial_reader_esp32)
        status_layout.addWidget(self.lead_control)
        self.data_recorder_control = DataRecorderControlWidget(self.data_manager)
        status_layout.addWidget(self.data_recorder_control)
        self.plot_control = PlotControlWidget(self.data_manager)
        status_layout.addWidget(self.plot_control)
        layout.addLayout(status_layout)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)  # Update every 50ms

    @pyqtSlot()
    def update_ui(self):
        update_plot(self.data_manager, self.line_raw, self.status_text, self.ax)
        self.canvas.draw()

        # Update status widgets
        with self.data_manager.data_lock:
            current_lead = get_current_lead(self.data_manager.current_lead_index)
            discharge_list = list(self.data_manager.discharge_events)
            last_discharge_time = f"{discharge_list[-1][2]:.0f} ms" if discharge_list else "N/A"

            # Update device status
            self.device_status.update_status(
                esp32_connected=self.data_manager.esp32_connected,
                arduino_connected=self.data_manager.arduino_connected
            )

            # Update cardioversor status
            self.cardioversor_status.update_status(
                current_lead=current_lead,
                charge_energy=self.data_manager.energia_carga_actual,
                phase1_energy=self.data_manager.energia_fase1_actual,
                phase2_energy=self.data_manager.energia_fase2_actual,
                total_energy=self.data_manager.energia_total_ciclo,
                last_discharge_time=last_discharge_time,
                total_discharges=len(self.data_manager.discharge_events)
            )

        # Update data recorder status
        self.data_recorder_control.update_status()


class PlotControlWidget(QGroupBox):
    def __init__(self, data_manager):
        super().__init__("Plot Controls")
        self.data_manager = data_manager
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Y-axis amplitude controls
        layout.addWidget(QLabel("Y Min:"), 0, 0)
        self.y_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_min_slider.setRange(-20, 40)
        self.y_min_slider.setValue(int(self.data_manager.plot_y_min * 10))
        self.y_min_slider.valueChanged.connect(self.on_y_min_changed)
        layout.addWidget(self.y_min_slider, 0, 1)

        self.y_min_label = QLabel(f"{self.data_manager.plot_y_min:.1f}")
        layout.addWidget(self.y_min_label, 0, 2)

        layout.addWidget(QLabel("Y Max:"), 1, 0)
        self.y_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_max_slider.setRange(-20, 40)
        self.y_max_slider.setValue(int(min(self.data_manager.plot_y_max * 10, 40)))  # Cap at 4.0V
        self.y_max_slider.valueChanged.connect(self.on_y_max_changed)
        layout.addWidget(self.y_max_slider, 1, 1)

        self.y_max_label = QLabel(f"{self.data_manager.plot_y_max:.1f}")
        layout.addWidget(self.y_max_label, 1, 2)

        # Window size control
        layout.addWidget(QLabel("Window Size:"), 2, 0)
        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(500, 5000)
        self.window_size_spin.setValue(self.data_manager.plot_window_size)
        self.window_size_spin.setSingleStep(100)
        self.window_size_spin.valueChanged.connect(self.on_window_size_changed)
        layout.addWidget(self.window_size_spin, 2, 1)

        # Signal gain control
        layout.addWidget(QLabel("Signal Gain:"), 4, 0)
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(1, 100)  # 0.1x to 10x gain
        self.gain_slider.setValue(int(self.data_manager.signal_gain * 10))
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        layout.addWidget(self.gain_slider, 4, 1)

        self.gain_label = QLabel(f"{self.data_manager.signal_gain:.1f}x")
        layout.addWidget(self.gain_label, 4, 2)

        # Time axis toggle
        layout.addWidget(QLabel("Time Axis:"), 5, 0)
        self.time_axis_check = QCheckBox("Use Time (s)")
        self.time_axis_check.setChecked(self.data_manager.plot_time_axis)
        self.time_axis_check.stateChanged.connect(self.on_time_axis_changed)
        layout.addWidget(self.time_axis_check, 5, 1)

        self.setLayout(layout)

    def on_y_min_changed(self, value):
        y_min = value / 10.0
        with self.data_manager.data_lock:
            self.data_manager.plot_y_min = y_min
        self.y_min_label.setText(f"{y_min:.1f}")

    def on_y_max_changed(self, value):
        y_max = value / 10.0
        with self.data_manager.data_lock:
            self.data_manager.plot_y_max = y_max
        self.y_max_label.setText(f"{y_max:.1f}")

    def on_window_size_changed(self, value):
        with self.data_manager.data_lock:
            self.data_manager.plot_window_size = value

    def on_gain_changed(self, value):
        gain = value / 10.0
        with self.data_manager.data_lock:
            self.data_manager.signal_gain = gain
        self.gain_label.setText(f"{gain:.1f}x")

    def on_time_axis_changed(self, state):
        with self.data_manager.data_lock:
            self.data_manager.plot_time_axis = (state == Qt.CheckState.Checked)

    def closeEvent(self, event):
        self.timer.stop()
        self.serial_reader_esp32.stop()
        self.serial_reader_arduino.stop()
        self.data_manager.data_recorder.close()
        event.accept()