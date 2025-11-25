import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
from .config import WINDOW_SIZE, Y_MIN, Y_MAX, MIN_PEAK_DISTANCE, POST_R_DELAY_SAMPLES
from .utils import detect_r_peaks_improved, calculate_post_r_markers, get_current_lead

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

def setup_plot(data_manager, serial_reader_esp32):
    """Configura la interfaz gráfica"""
    plt.style.use('default')

    fig = plt.figure(figsize=(14, 8))

    # Grid layout ajustado
    gs = fig.add_gridspec(4, 4, height_ratios=[2, 2, 1, 0.4], width_ratios=[1, 1, 1, 0.35],
                          hspace=0.35, wspace=0.30, left=0.06, right=0.97, top=0.96, bottom=0.06)

    fig.patch.set_facecolor('#FFE4E1')

    # ECG Original
    ax1 = fig.add_subplot(gs[0, 0:3])
    ax1.set_facecolor('#FFE4E1')
    ax1.set_xlim(0, WINDOW_SIZE)
    ax1.set_ylim(Y_MIN, Y_MAX)
    ax1.set_ylabel('Voltaje (V)', color='black', fontweight='bold')
    ax1.set_title('Monitor ECG - Señal Original (ESP32)', color='black', fontweight='bold', fontsize=12, pad=15)
    ax1.grid(True, color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    ax1.minorticks_on()

    # ECG Filtrada
    ax2 = fig.add_subplot(gs[1, 0:3], sharex=ax1)
    ax2.set_facecolor('#FFE4E1')
    ax2.set_xlim(0, WINDOW_SIZE)
    ax2.set_ylim(-0.3, 0.3)
    ax2.set_xlabel('Muestras', color='black', fontweight='bold')
    ax2.set_ylabel('Voltaje (V)', color='black', fontweight='bold')
    ax2.set_title('Señal con Baseline EMA + Picos R', color='black', fontweight='bold', fontsize=12, pad=15)
    ax2.grid(True, color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    ax2.minorticks_on()

    # Panel de información
    ax_info = fig.add_subplot(gs[0:2, 3])
    ax_info.axis('off')

    # Gráfica de descarga bifásica
    ax3 = fig.add_subplot(gs[2, 0:3])
    ax3.set_facecolor('#FFFACD')
    ax3.set_title('Descarga Bifásica (Capacitor)', color='black', fontweight='bold', fontsize=10)
    ax3.set_xlabel('Tiempo (ms)', color='black', fontsize=9)
    ax3.set_ylabel('Voltaje (V)', color='black', fontsize=9)
    ax3.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)

    # Botones de derivación
    ax_btn_di = fig.add_subplot(gs[3, 0])
    ax_btn_dii = fig.add_subplot(gs[3, 1])
    ax_btn_diii = fig.add_subplot(gs[3, 2])
    ax_btn_avr = fig.add_subplot(gs[3, 3])

    btn_di = Button(ax_btn_di, 'DI', color='lightblue', hovercolor='blue')
    btn_di.on_clicked(lambda event: on_lead_di_button(event, data_manager, serial_reader_esp32))

    btn_dii = Button(ax_btn_dii, 'DII', color='lightgreen', hovercolor='green')
    btn_dii.on_clicked(lambda event: on_lead_dii_button(event, data_manager, serial_reader_esp32))

    btn_diii = Button(ax_btn_diii, 'DIII', color='lightyellow', hovercolor='yellow')
    btn_diii.on_clicked(lambda event: on_lead_diii_button(event, data_manager, serial_reader_esp32))

    btn_avr = Button(ax_btn_avr, 'aVR', color='lightcoral', hovercolor='red')
    btn_avr.on_clicked(lambda event: on_lead_avr_button(event, data_manager, serial_reader_esp32))

    # Líneas de ECG
    line_raw, = ax1.plot([], [], 'black', linewidth=1.2, alpha=0.95, label='ECG Cruda')
    line_filtered, = ax2.plot([], [], 'black', linewidth=1.5, label='ECG Filtrada')
    line_baseline, = ax2.plot([], [], 'b--', linewidth=1, alpha=0.5, label='Baseline')
    peaks_line, = ax2.plot([], [], 'ro', markersize=6, alpha=0.8, label='Picos R')
    post_r_line, = ax2.plot([], [], 'bo', markersize=5, alpha=0.8, label='20ms post-R')
    discharge_line, = ax2.plot([], [], 'co', markersize=10, alpha=0.6, fillstyle='none',
                                markeredgewidth=2, label='Descargas')

    # Línea de descarga bifásica
    line_descarga, = ax3.plot([], [], 'red', linewidth=2, label='Voltaje Capacitor')

    status_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes,
                           verticalalignment='top', fontsize=7, color='black',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.9, edgecolor='gray'))

    info_text = ax_info.text(0.05, 0.95, '', transform=ax_info.transAxes,
                             verticalalignment='top', fontsize=8, color='black', family='monospace',
                             bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                                      alpha=0.95, edgecolor='black', linewidth=2))

    ax1.legend(loc='upper right', fontsize=8, ncol=1)
    ax2.legend(loc='upper right', fontsize=7, ncol=6)
    ax3.legend(loc='upper right', fontsize=8)

    return (fig, ax1, ax2, ax3, ax_info, line_raw, line_filtered, line_baseline,
            peaks_line, post_r_line, discharge_line, line_descarga,
            status_text, info_text, btn_di, btn_dii, btn_diii, btn_avr)

def update_plot(frame, data_manager, line_raw, line_filtered, line_baseline, peaks_line, post_r_line, discharge_line, line_descarga, status_text, info_text, ax1, ax2, ax3):
    """Actualiza la visualización"""
    with data_manager.data_lock:
        if len(data_manager.voltage_buffer) == 0:
            return (line_raw, line_filtered, line_baseline, peaks_line,
                    post_r_line, discharge_line, line_descarga, status_text, info_text)

        y_raw = list(data_manager.voltage_buffer)
        y_filtered = list(data_manager.filtered_buffer)
        y_baseline = list(data_manager.baseline_buffer)
        x_data = list(data_manager.time_buffer)
        discharge_list = list(data_manager.discharge_events)

        # Datos de descarga bifásica
        y_descarga = list(data_manager.descarga_voltage_buffer)
        x_descarga = list(data_manager.descarga_time_buffer)

    # Ventana visible ECG
    if len(y_raw) > WINDOW_SIZE:
        start_idx = len(y_raw) - WINDOW_SIZE
        y_raw_visible = y_raw[start_idx:]
        y_filtered_visible = y_filtered[start_idx:]
        y_baseline_visible = y_baseline[start_idx:]
        x_visible = x_data[start_idx:]
    else:
        y_raw_visible = y_raw
        y_filtered_visible = y_filtered
        y_baseline_visible = y_baseline
        x_visible = x_data

    line_raw.set_data(x_visible, y_raw_visible)
    line_filtered.set_data(x_visible, y_filtered_visible)
    line_baseline.set_data([], [])

    # Detectar picos R
    if len(y_filtered_visible) > MIN_PEAK_DISTANCE * 2:
        peaks_idx = detect_r_peaks_improved(y_filtered_visible)
        if peaks_idx:
            peaks_x = [x_visible[i] for i in peaks_idx if i < len(x_visible)]
            peaks_y = [y_filtered_visible[i] for i in peaks_idx if i < len(y_filtered_visible)]
            peaks_line.set_data(peaks_x, peaks_y)

            post_r_indices = calculate_post_r_markers(peaks_idx)
            post_r_x = []
            post_r_y = []

            for post_r_idx in post_r_indices:
                if post_r_idx < len(x_visible) and post_r_idx < len(y_filtered_visible):
                    post_r_x.append(x_visible[post_r_idx])
                    post_r_y.append(y_filtered_visible[post_r_idx])

            post_r_line.set_data(post_r_x, post_r_y)
        else:
            peaks_line.set_data([], [])
            post_r_line.set_data([], [])
    else:
        peaks_line.set_data([], [])
        post_r_line.set_data([], [])

    # Marcadores de descarga
    discharge_x = []
    discharge_y = []
    for discharge_sample, discharge_time, tiempo_desde_r in discharge_list:
        for idx, x_val in enumerate(x_visible):
            if abs(x_val - discharge_sample) < 10 and idx < len(y_filtered_visible):
                discharge_x.append(x_visible[idx])
                discharge_y.append(y_filtered_visible[idx])
                break
    discharge_line.set_data(discharge_x, discharge_y)

    # Actualizar gráfica de descarga bifásica
    if len(x_descarga) > 0 and len(y_descarga) > 0:
        line_descarga.set_data(x_descarga, y_descarga)
        ax3.set_xlim(0, max(x_descarga) + 100 if max(x_descarga) > 0 else 1000)
        ax3.set_ylim(0, max(y_descarga) + 2 if max(y_descarga) > 0 else 30)
    else:
        line_descarga.set_data([], [])

    # Ajustar límites X
    if len(x_visible) > 0:
        x_min = x_visible[0]
        x_max = x_visible[-1] if len(x_visible) > WINDOW_SIZE else x_visible[0] + WINDOW_SIZE
        ax1.set_xlim(x_min, x_max)
        ax2.set_xlim(x_min, x_max)

        if len(y_filtered_visible) > 0:
            y_min_filt = min(y_filtered_visible)
            y_max_filt = max(y_filtered_visible)
            y_margin = 0.2 * (y_max_filt - y_min_filt) if y_max_filt != y_min_filt else 0.1
            ax2.set_ylim(y_min_filt - y_margin, y_max_filt + y_margin)

    with data_manager.data_lock:
        # Indicadores de conexión
        esp32_status = "ESP32 OK" if data_manager.esp32_connected else "ESP32 ERR"
        arduino_status = "ARD OK" if data_manager.arduino_connected else "ARD ERR"

        current_lead = get_current_lead(data_manager.current_lead_index)

        ultimo_tiempo_descarga = "N/A"
        if discharge_list:
            ultimo_tiempo_descarga = f"{discharge_list[-1][2]:.0f} ms"

        status_text.set_text(
            f"{esp32_status} | {arduino_status} | Muestras: {len(y_raw)} | Filtro: Baseline EMA"
        )

        # Panel de información
        info_text.set_text(
            f"╔══════════════╗\n"
            f"║  INFO ECG   ║\n"
            f"╠══════════════╣\n"
            f"║ CONEXIONES   ║\n"
            f"║ ESP32: {'✓' if data_manager.esp32_connected else '✗':>5s}  ║\n"
            f"║ ARD:   {'✓' if data_manager.arduino_connected else '✗':>5s}  ║\n"
            f"╠══════════════╣\n"
            f"║ DERIVACIÓN   ║\n"
            f"║   {current_lead:^4s}       ║\n"
            f"║ (Manual)     ║\n"
            f"╠══════════════╣\n"
            f"║ ENERGÍAS (J) ║\n"
            f"║ Carga:       ║\n"
            f"║  {data_manager.energia_carga_actual:>6.2f}      ║\n"
            f"║ Fase 1:      ║\n"
            f"║  {data_manager.energia_fase1_actual:>6.3f}      ║\n"
            f"║ Fase 2:      ║\n"
            f"║  {data_manager.energia_fase2_actual:>6.3f}      ║\n"
            f"║ Total:       ║\n"
            f"║  {data_manager.energia_total_ciclo:>6.3f}      ║\n"
            f"╠══════════════╣\n"
            f"║ ÚLTIMA DESC. ║\n"
            f"║ {ultimo_tiempo_descarga:>9s}  ║\n"
            f"║ (desde R)    ║\n"
            f"╠══════════════╣\n"
            f"║ TOTAL DESC.  ║\n"
            f"║     {len(data_manager.discharge_events):>3d}       ║\n"
            f"╚══════════════╝"
        )

    return (line_raw, line_filtered, line_baseline, peaks_line,
            post_r_line, discharge_line, line_descarga, status_text, info_text)