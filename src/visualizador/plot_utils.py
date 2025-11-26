import matplotlib
matplotlib.use('QtAgg')  # Use PyQt6 backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .config import SAMPLE_RATE
from .utils import get_current_lead

def on_lead_di_button(event, ui_service, serial_reader_esp32):
    """Cambiar a derivación DI"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DI")
        ui_service.current_lead_index = 0
        print("Cambio a derivacion DI")

def on_lead_dii_button(event, ui_service, serial_reader_esp32):
    """Cambiar a derivación DII"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DII")
        ui_service.current_lead_index = 1
        print("Cambio a derivacion DII")

def on_lead_diii_button(event, ui_service, serial_reader_esp32):
    """Cambiar a derivación DIII"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DIII")
        ui_service.current_lead_index = 2
        print("Cambio a derivacion DIII")

def on_lead_avr_button(event, ui_service, serial_reader_esp32):
    """Cambiar a derivación aVR"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("AVR")
        ui_service.current_lead_index = 3
        print("Cambio a derivacion aVR")

def on_charge_button(event, data_manager):
    """Callback para botón de carga manual"""
    with data_manager.data_lock:
        data_manager.force_charge = True
    print("🔋 Comando de CARGA MANUAL activado")

def on_discharge_button(event, data_manager):
    """Callback para botón de descarga manual"""
    with data_manager.data_lock:
        data_manager.force_discharge = True
    print("Comando de DESCARGA MANUAL activado")

def setup_plot(ui_service):
    """Configura la interfaz gráfica para ADC raw"""
    plt.style.use('default')

    fig = Figure(figsize=(10, 6))
    fig.patch.set_facecolor('#FFE4E1')

    ax = fig.add_subplot(111)
    ax.set_facecolor('#FFE4E1')
    ax.set_xlim(0, ui_service.plot_window_size)
    ax.set_ylim(ui_service.plot_y_min, ui_service.plot_y_max)
    ax.set_ylabel('Voltaje (V)', color='black', fontweight='bold')
    xlabel = 'Tiempo (s)' if ui_service.plot_time_axis else 'Muestras'
    ax.set_xlabel(xlabel, color='black', fontweight='bold')
    ax.set_title('Monitor ECG - Señal ADC Raw (ESP32)', color='black', fontweight='bold', fontsize=12, pad=15)
    ax.grid(True, color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    ax.minorticks_on()

    line_raw, = ax.plot([], [], 'black', linewidth=1.2, alpha=0.95, label='ECG Raw')
    ax.legend(loc='upper right', fontsize=8)

    status_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                           verticalalignment='top', fontsize=7, color='black',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor='gray'))

    canvas = FigureCanvas(fig)
    return canvas, ax, line_raw, status_text

def update_plot(ui_service, line_raw, status_text, ax):
    """Actualiza la visualización del ADC raw"""
    if len(ui_service.voltage_buffer) == 0:
        return

    y_raw = list(ui_service.voltage_buffer)
    x_data = list(ui_service.time_buffer)
    window_size = ui_service.plot_window_size
    time_axis = ui_service.plot_time_axis
    y_min = ui_service.plot_y_min
    y_max = ui_service.plot_y_max

    # Ventana visible
    if len(y_raw) > window_size:
        start_idx = len(y_raw) - window_size
        y_raw_visible = y_raw[start_idx:]
        x_visible = x_data[start_idx:]
    else:
        y_raw_visible = y_raw
        x_visible = x_data

    # Convert to time axis if enabled
    if time_axis:
        x_visible = [x / SAMPLE_RATE for x in x_visible]

    line_raw.set_data(x_visible, y_raw_visible)

    # Update axis limits
    ax.set_ylim(y_min, y_max)
    if len(x_visible) > 0:
        x_min = x_visible[0]
        x_max = x_visible[-1] if len(x_visible) > window_size else x_visible[0] + (window_size / SAMPLE_RATE if time_axis else window_size)
        ax.set_xlim(x_min, x_max)

    # Update labels
    ax.set_xlabel('Tiempo (s)' if time_axis else 'Muestras')

    # Indicadores de conexión
    esp32_status = "ESP32 OK" if ui_service.esp32_connected else "ESP32 ERR"
    arduino_status = "ARD OK" if ui_service.arduino_connected else "ARD ERR"

    status_text.set_text(
        f"{esp32_status} | {arduino_status} | Muestras: {len(y_raw)}"
    )