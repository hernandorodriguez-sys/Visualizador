import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from .config import SAMPLE_RATE

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
    """Configura la interfaz gráfica para ADC raw usando PyQtGraph"""
    # Create PlotWidget
    plot_widget = pg.PlotWidget()
    plot_widget.setBackground('#FFE4E1')
    plot_widget.setTitle('Monitor ECG - Señal ADC Raw (ESP32)', color='black', size='12pt')
    plot_widget.setLabel('left', 'Voltaje (V)', color='black')
    xlabel = 'Tiempo (s)' if ui_service.plot_time_axis else 'Muestras'
    plot_widget.setLabel('bottom', xlabel, color='black')

    # Set initial ranges
    plot_widget.setXRange(0, ui_service.plot_window_size)
    plot_widget.setYRange(ui_service.plot_y_min, ui_service.plot_y_max)

    # Enable grid
    plot_widget.showGrid(x=True, y=True, alpha=0.7)

    # Create plot item for ECG data
    line_raw = plot_widget.plot([], [], pen=pg.mkPen('black', width=1.2, alpha=0.95), name='ECG Raw')

    # Create scatter plot item for R-peaks
    r_peak_scatter = pg.ScatterPlotItem(size=8, pen=pg.mkPen('red'), brush=pg.mkBrush('red'), symbol='o', name='R-Peaks')
    plot_widget.addItem(r_peak_scatter)

    # Add legend
    legend = pg.LegendItem((80, 60), offset=(70, 20))
    legend.setParentItem(plot_widget.graphicsItem())
    legend.addItem(line_raw, 'ECG Raw')
    legend.addItem(r_peak_scatter, 'R-Peaks')

    # Status text item
    status_text = pg.TextItem('', anchor=(0, 1), color='black')
    status_text.setPos(0.02, 0.98)
    plot_widget.addItem(status_text)

    return plot_widget, line_raw, r_peak_scatter, status_text

def update_plot(ui_service, plot_widget, line_raw, r_peak_scatter, status_text):
    """Actualiza la visualización del ADC raw usando PyQtGraph"""
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

    # Make x relative to start from 0 for real-time plotting
    if len(x_visible) > 0:
        x_offset = x_visible[0]
        x_visible = [x - x_offset for x in x_visible]

    # Convert to time axis if enabled
    if time_axis:
        x_visible = [x / SAMPLE_RATE for x in x_visible]

    # Update plot data
    line_raw.setData(x_visible, y_raw_visible)

    # Update axis limits
    plot_widget.setYRange(y_min, y_max)
    if len(x_visible) > 0:
        x_min = x_visible[0]
        x_max = x_visible[-1] if len(x_visible) > window_size else x_visible[0] + (window_size / SAMPLE_RATE if time_axis else window_size)
        plot_widget.setXRange(x_min, x_max)

    # Update labels
    xlabel = 'Tiempo (s)' if time_axis else 'Muestras'
    plot_widget.setLabel('bottom', xlabel, color='black')

    # Update R-peak markers
    if hasattr(ui_service, 'r_peak_buffer') and ui_service.r_peak_buffer:
        # Filter R-peaks within the visible window
        visible_r_peaks = []
        for peak_sample_idx in ui_service.r_peak_buffer:
            # peak_sample_idx is the absolute index in the full buffers
            # Check if this peak is within the visible window
            if start_idx <= peak_sample_idx < len(ui_service.voltage_buffer):
                # Calculate position relative to visible window
                relative_idx = peak_sample_idx - start_idx
                if 0 <= relative_idx < len(x_visible):
                    peak_voltage = ui_service.voltage_buffer[peak_sample_idx]
                    peak_x_pos = x_visible[relative_idx]
                    visible_r_peaks.append({'pos': (peak_x_pos, peak_voltage), 'size': 8, 'pen': 'r', 'brush': 'r'})

        r_peak_scatter.setData(visible_r_peaks)
    else:
        r_peak_scatter.setData([])

    # Indicadores de conexión
    esp32_status = "ESP32 OK" if ui_service.esp32_connected else "ESP32 ERR"
    arduino_status = "ARD OK" if ui_service.arduino_connected else "ARD ERR"

    status_text.setText(
        f"{esp32_status} | {arduino_status} | Muestras: {len(y_raw)}"
    )