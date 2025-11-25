import matplotlib
matplotlib.use('QtAgg')  # Use PyQt6 backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .config import WINDOW_SIZE, Y_MIN, Y_MAX
from .utils import get_current_lead

def on_lead_di_button(event, data_manager, serial_reader_esp32):
    """Cambiar a derivación DI"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DI")
        with data_manager.data_lock:
            data_manager.current_lead_index = 0
        print("Cambio a derivacion DI")

def on_lead_dii_button(event, data_manager, serial_reader_esp32):
    """Cambiar a derivación DII"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DII")
        with data_manager.data_lock:
            data_manager.current_lead_index = 1
        print("Cambio a derivacion DII")

def on_lead_diii_button(event, data_manager, serial_reader_esp32):
    """Cambiar a derivación DIII"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("DIII")
        with data_manager.data_lock:
            data_manager.current_lead_index = 2
        print("Cambio a derivacion DIII")

def on_lead_avr_button(event, data_manager, serial_reader_esp32):
    """Cambiar a derivación aVR"""
    if serial_reader_esp32:
        serial_reader_esp32.send_lead_command("AVR")
        with data_manager.data_lock:
            data_manager.current_lead_index = 3
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

def setup_plot():
    """Configura la interfaz gráfica para ADC raw"""
    plt.style.use('default')

    fig = Figure(figsize=(10, 6))
    fig.patch.set_facecolor('#FFE4E1')

    ax = fig.add_subplot(111)
    ax.set_facecolor('#FFE4E1')
    ax.set_xlim(0, WINDOW_SIZE)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_ylabel('Voltaje (V)', color='black', fontweight='bold')
    ax.set_xlabel('Muestras', color='black', fontweight='bold')
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

def update_plot(data_manager, line_raw, status_text, ax):
    """Actualiza la visualización del ADC raw"""
    with data_manager.data_lock:
        if len(data_manager.voltage_buffer) == 0:
            return

        y_raw = list(data_manager.voltage_buffer)
        x_data = list(data_manager.time_buffer)

    # Ventana visible
    if len(y_raw) > WINDOW_SIZE:
        start_idx = len(y_raw) - WINDOW_SIZE
        y_raw_visible = y_raw[start_idx:]
        x_visible = x_data[start_idx:]
    else:
        y_raw_visible = y_raw
        x_visible = x_data

    line_raw.set_data(x_visible, y_raw_visible)

    # Ajustar límites X
    if len(x_visible) > 0:
        x_min = x_visible[0]
        x_max = x_visible[-1] if len(x_visible) > WINDOW_SIZE else x_visible[0] + WINDOW_SIZE
        ax.set_xlim(x_min, x_max)

    with data_manager.data_lock:
        # Indicadores de conexión
        esp32_status = "ESP32 OK" if data_manager.esp32_connected else "ESP32 ERR"
        arduino_status = "ARD OK" if data_manager.arduino_connected else "ARD ERR"

        status_text.set_text(
            f"{esp32_status} | {arduino_status} | Muestras: {len(y_raw)}"
        )