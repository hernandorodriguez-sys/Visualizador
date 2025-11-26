import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QGroupBox, QGridLayout, QMessageBox, QSlider, QCheckBox, QSpinBox
from PyQt6.QtCore import QTimer, pyqtSlot, Qt
from .plot_utils import setup_plot, update_plot, on_lead_di_button, on_lead_dii_button, on_lead_diii_button, on_lead_avr_button
from .ui_service import UIService
from .serial_readers import SerialReaderESP32, SerialReaderArduino

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
    def __init__(self, ui_service, serial_reader_esp32):
        super().__init__("Control Derivada")
        self.ui_service = ui_service
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
            on_lead_di_button(None, self.ui_service, self.serial_reader_esp32)
        elif lead == 'DII':
            on_lead_dii_button(None, self.ui_service, self.serial_reader_esp32)
        elif lead == 'DIII':
            on_lead_diii_button(None, self.ui_service, self.serial_reader_esp32)
        elif lead == 'aVR':
            on_lead_avr_button(None, self.ui_service, self.serial_reader_esp32)


class DataRecorderControlWidget(QGroupBox):
    def __init__(self, ui_service):
        super().__init__("Data Recorder")
        self.ui_service = ui_service
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

        self.status_label = QLabel("Recording: OFF")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def on_start_clicked(self):
        self.ui_service.data_recorder.start_recording()
        self.update_status()

    def on_stop_clicked(self):
        self.ui_service.data_recorder.stop_recording()
        self.update_status()

    def update_status(self):
        is_recording = self.ui_service.data_recorder.is_recording
        if is_recording:
            self.status_label.setText("Recording: ON")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.status_label.setText("Recording: OFF")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")


class MainWindow(QMainWindow):
    def __init__(self, ui_service, adc_service):
        super().__init__()
        self.ui_service = ui_service
        self.adc_service = adc_service
        self.serial_reader_esp32 = adc_service.esp32_reader
        self.serial_reader_arduino = adc_service.arduino_reader

        self.setWindowTitle("Monitor ECG - ADC Raw")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # PyQtGraph plot widget
        self.plot_widget, self.line_raw, self.status_text = setup_plot(self.ui_service)
        layout.addWidget(self.plot_widget)

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
        self.lead_control = LeadControlWidget(self.ui_service, self.serial_reader_esp32)
        status_layout.addWidget(self.lead_control)
        self.data_recorder_control = DataRecorderControlWidget(self.ui_service)
        status_layout.addWidget(self.data_recorder_control)
        self.plot_control = PlotControlWidget(self.ui_service)
        status_layout.addWidget(self.plot_control)
        self.bandpass_filter_control = BandPassFilterWidget(self.adc_service.signal_processing_service)
        status_layout.addWidget(self.bandpass_filter_control)
        layout.addLayout(status_layout)

        # UI updates are now handled by the UI service


class PlotControlWidget(QGroupBox):
    def __init__(self, ui_service):
        super().__init__("Plot Controls")
        self.ui_service = ui_service
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Y-axis amplitude controls
        layout.addWidget(QLabel("Y Min:"), 0, 0)
        self.y_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_min_slider.setRange(-20, 40)
        self.y_min_slider.setValue(int(self.ui_service.plot_y_min * 10))
        self.y_min_slider.valueChanged.connect(self.on_y_min_changed)
        layout.addWidget(self.y_min_slider, 0, 1)

        self.y_min_label = QLabel(f"{self.ui_service.plot_y_min:.1f}")
        layout.addWidget(self.y_min_label, 0, 2)

        layout.addWidget(QLabel("Y Max:"), 1, 0)
        self.y_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_max_slider.setRange(-20, 40)
        self.y_max_slider.setValue(int(min(self.ui_service.plot_y_max * 10, 40)))  # Cap at 4.0V
        self.y_max_slider.valueChanged.connect(self.on_y_max_changed)
        layout.addWidget(self.y_max_slider, 1, 1)

        self.y_max_label = QLabel(f"{self.ui_service.plot_y_max:.1f}")
        layout.addWidget(self.y_max_label, 1, 2)

        # Window size control
        layout.addWidget(QLabel("Window Size:"), 2, 0)
        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(500, 5000)
        self.window_size_spin.setValue(self.ui_service.plot_window_size)
        self.window_size_spin.setSingleStep(100)
        self.window_size_spin.valueChanged.connect(self.on_window_size_changed)
        layout.addWidget(self.window_size_spin, 2, 1)

        # Signal gain control
        layout.addWidget(QLabel("Signal Gain:"), 4, 0)
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(1, 100)  # 0.1x to 10x gain
        self.gain_slider.setValue(int(self.ui_service.signal_gain * 10))
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        layout.addWidget(self.gain_slider, 4, 1)

        self.gain_label = QLabel(f"{self.ui_service.signal_gain:.1f}x")
        layout.addWidget(self.gain_label, 4, 2)

        # Time axis toggle
        layout.addWidget(QLabel("Time Axis:"), 5, 0)
        self.time_axis_check = QCheckBox("Use Time (s)")
        self.time_axis_check.setChecked(self.ui_service.plot_time_axis)
        self.time_axis_check.stateChanged.connect(self.on_time_axis_changed)
        layout.addWidget(self.time_axis_check, 5, 1)

        self.setLayout(layout)

    def on_y_min_changed(self, value):
        y_min = value / 10.0
        self.ui_service.plot_y_min = y_min
        self.y_min_label.setText(f"{y_min:.1f}")

    def on_y_max_changed(self, value):
        y_max = value / 10.0
        self.ui_service.plot_y_max = y_max
        self.y_max_label.setText(f"{y_max:.1f}")

    def on_window_size_changed(self, value):
        self.ui_service.plot_window_size = value

    def on_gain_changed(self, value):
        gain = value / 10.0
        self.ui_service.signal_gain = gain
        self.gain_label.setText(f"{gain:.1f}x")

    def on_time_axis_changed(self, state):
        self.ui_service.plot_time_axis = (state == Qt.CheckState.Checked)


class BandPassFilterWidget(QGroupBox):
    def __init__(self, signal_processing_service):
        super().__init__("Band Pass Filter")
        self.signal_processing_service = signal_processing_service
        # Store current displayed values (preview mode)
        self.displayed_low_cutoff = self.signal_processing_service.low_cutoff
        self.displayed_high_cutoff = self.signal_processing_service.high_cutoff
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # High-pass frequency controls
        layout.addWidget(QLabel("High-Pass (Hz):"), 0, 0)
        self.low_cutoff_label = QLabel(f"{self.displayed_low_cutoff:.2f}")
        layout.addWidget(self.low_cutoff_label, 0, 1)

        low_btn_layout = QHBoxLayout()
        self.low_minus_btn = QPushButton("-")
        self.low_minus_btn.clicked.connect(self.on_low_minus_clicked)
        low_btn_layout.addWidget(self.low_minus_btn)

        self.low_plus_btn = QPushButton("+")
        self.low_plus_btn.clicked.connect(self.on_low_plus_clicked)
        low_btn_layout.addWidget(self.low_plus_btn)

        layout.addLayout(low_btn_layout, 0, 2)

        # Low-pass frequency controls
        layout.addWidget(QLabel("Low-Pass (Hz):"), 1, 0)
        self.high_cutoff_label = QLabel(f"{self.displayed_high_cutoff:.1f}")
        layout.addWidget(self.high_cutoff_label, 1, 1)

        high_btn_layout = QHBoxLayout()
        self.high_minus_btn = QPushButton("-")
        self.high_minus_btn.clicked.connect(self.on_high_minus_clicked)
        high_btn_layout.addWidget(self.high_minus_btn)

        self.high_plus_btn = QPushButton("+")
        self.high_plus_btn.clicked.connect(self.on_high_plus_clicked)
        high_btn_layout.addWidget(self.high_plus_btn)

        layout.addLayout(high_btn_layout, 1, 2)

        # Set and Reset buttons
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.on_reset_clicked)
        button_layout.addWidget(self.reset_button)

        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.on_set_clicked)
        button_layout.addWidget(self.set_button)

        layout.addLayout(button_layout, 2, 0, 1, 3)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label, 3, 0, 1, 3)

        self.setLayout(layout)

    def on_low_minus_clicked(self):
        self.displayed_low_cutoff = max(0.05, self.displayed_low_cutoff - 0.05)
        self.low_cutoff_label.setText(f"{self.displayed_low_cutoff:.2f}")
        self.clear_status()

    def on_low_plus_clicked(self):
        self.displayed_low_cutoff += 0.05
        self.low_cutoff_label.setText(f"{self.displayed_low_cutoff:.2f}")
        self.clear_status()

    def on_high_minus_clicked(self):
        self.displayed_high_cutoff = max(1.0, self.displayed_high_cutoff - 5.0)
        self.high_cutoff_label.setText(f"{self.displayed_high_cutoff:.1f}")
        self.clear_status()

    def on_high_plus_clicked(self):
        self.displayed_high_cutoff += 5.0
        self.high_cutoff_label.setText(f"{self.displayed_high_cutoff:.1f}")
        self.clear_status()

    def on_set_clicked(self):
        # Validate parameters
        if self.displayed_low_cutoff >= self.displayed_high_cutoff:
            QMessageBox.warning(self, "Invalid Filter Parameters",
                              "High-pass frequency must be less than low-pass frequency.")
            return

        # Apply the filter parameters
        success = self.signal_processing_service.update_filter_parameters(
            self.displayed_low_cutoff, self.displayed_high_cutoff)

        if success:
            self.status_label.setText("Setted!")
            # Update actual values to match displayed
            self.signal_processing_service.low_cutoff = self.displayed_low_cutoff
            self.signal_processing_service.high_cutoff = self.displayed_high_cutoff
        else:
            QMessageBox.warning(self, "Invalid Filter Parameters",
                              "Filter parameters are out of valid range.")
            self.status_label.setText("")

    def on_reset_clicked(self):
        self.displayed_low_cutoff = 0.05
        self.displayed_high_cutoff = 50.0
        self.low_cutoff_label.setText("0.05")
        self.high_cutoff_label.setText("50.0")
        self.clear_status()

    def clear_status(self):
        self.status_label.setText("")


    def closeEvent(self, event):
        self.timer.stop()
        self.serial_reader_esp32.stop()
        self.serial_reader_arduino.stop()
        self.ui_service.data_recorder.close()
        event.accept()