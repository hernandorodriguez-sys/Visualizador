import time
import threading
import matplotlib.animation as animation
import matplotlib.pyplot as plt

from config import SERIAL_PORT_ESP32, SERIAL_PORT_ARDUINO, BAUD_RATE, refresh_interval
from data_manager import DataManager
from serial_readers import SerialReaderESP32, SerialReaderArduino
from plot_utils import setup_plot, update_plot
from utils import init_csv

def main():
    print("=" * 70)
    print("MONITOR ECG - CONTROL MANUAL DE DERIVACIONES")
    print("=" * 70)
    print(f"ESP32 (ECG):       {SERIAL_PORT_ESP32}")
    print(f"Arduino (Control): {SERIAL_PORT_ARDUINO}")
    print(f"Baud Rate:         {BAUD_RATE}")
    print("-" * 70)
    print("CONTROL DE DERIVACIONES:")
    print("  Boton DI   - Derivacion I")
    print("  Boton DII  - Derivacion II")
    print("  Boton DIII - Derivacion III")
    print("  Boton aVR  - Derivacion aVR")
    print("-" * 70)
    print("VISUALIZACION:")
    print("  • Senal ECG cruda (directo del ADC)")
    print("  • Senal ECG con baseline EMA")
    print("  • Deteccion automatica de picos R")
    print("  • Grafica de descarga bifasica del capacitor")
    print("  • Energias en tiempo real")
    print("=" * 70)
    print()

    # Initialize data manager
    data_manager = DataManager()
    data_manager.csv_filename, data_manager.csv_file, data_manager.csv_writer = init_csv()

    # Initialize serial readers
    serial_reader_esp32 = SerialReaderESP32(SERIAL_PORT_ESP32, BAUD_RATE)
    serial_reader_arduino = SerialReaderArduino(SERIAL_PORT_ARDUINO, BAUD_RATE)

    # Setup plot
    setup_result = setup_plot(data_manager, serial_reader_esp32)
    (fig, ax1, ax2, ax3, ax_info, line_raw, line_filtered, line_baseline,
     peaks_line, post_r_line, discharge_line, line_descarga,
     status_text, info_text, btn_di, btn_dii, btn_diii, btn_avr) = setup_result

    # Update plot setup with serial reader
    # Note: We need to recreate buttons with proper callbacks, but for simplicity, we'll handle it in the update function

    try:
        print("🚀 Iniciando lecturas seriales...\n")

        serial_reader_esp32.start(data_manager)
        time.sleep(1)
        serial_reader_arduino.start(data_manager)
        time.sleep(2)

        print("Ambos puertos seriales iniciados")
        print("   -> ESP32 leyendo ECG en COM7")
        print("   -> Arduino leyendo energia en COM8\n")

        def print_stats():
            while serial_reader_esp32.running:
                time.sleep(10)
                with data_manager.data_lock:  # Though counters are in serial_reader, to be safe
                    valid = serial_reader_esp32.valid_packets
                    invalid = serial_reader_esp32.invalid_packets
                if valid > 0:
                    error_rate = (invalid / (valid + invalid)) * 100
                    print(f"ESP32: {valid} paquetes validos, "
                          f"{invalid} invalidos ({error_rate:.2f}% error)")

        stats_thread = threading.Thread(target=print_stats, daemon=True)
        stats_thread.start()

        ani = animation.FuncAnimation(fig, lambda frame: update_plot(frame, data_manager, line_raw, line_filtered, line_baseline, peaks_line, post_r_line, discharge_line, line_descarga, status_text, info_text, ax1, ax2, ax3),
                                      interval=refresh_interval, blit=False, cache_frame_data=False)

        print("Abriendo ventana de visualizacion...\n")
        print("INSTRUCCIONES:")
        print("   • Usar botones para cambiar derivaciones manualmente")
        print("   • Grafica inferior muestra descarga bifasica\n")

        def on_close(event):
            print("\nCerrando aplicacion...")
            serial_reader_esp32.stop()
            serial_reader_arduino.stop()
            if data_manager.csv_file:
                data_manager.csv_file.close()
                print(f"Archivo CSV guardado: {data_manager.csv_filename}")
            plt.close('all')

        fig.canvas.mpl_connect('close_event', on_close)
        plt.show()

    except KeyboardInterrupt:
        print("\nInterrupcion por teclado - Cerrando...")
    except Exception as e:
        print(f"Error critico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCerrando conexiones seriales...")
        serial_reader_esp32.stop()
        serial_reader_arduino.stop()
        if data_manager.csv_file:
            data_manager.csv_file.close()
            print(f"Archivo CSV guardado: {data_manager.csv_filename}")
        print("Aplicacion cerrada correctamente")

if __name__ == "__main__":
    main()