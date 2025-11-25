import time
import threading
import sys
from PyQt6.QtWidgets import QApplication

from visualizador.config import SERIAL_PORT_ESP32, SERIAL_PORT_ARDUINO, BAUD_RATE
from visualizador.data_manager import DataManager
from visualizador.serial_readers import SerialReaderESP32, SerialReaderArduino
from visualizador.ui_main import MainWindow
from visualizador.utils import init_csv

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
    print("  • Senal ECG ADC Raw")
    print("=" * 70)
    print()

    # Initialize data manager
    data_manager = DataManager()
    data_manager.csv_filename, data_manager.csv_file, data_manager.csv_writer = init_csv()

    # Initialize serial readers
    serial_reader_esp32 = SerialReaderESP32(SERIAL_PORT_ESP32, BAUD_RATE)
    serial_reader_arduino = SerialReaderArduino(SERIAL_PORT_ARDUINO, BAUD_RATE)

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
                with data_manager.data_lock:
                    valid = serial_reader_esp32.valid_packets
                    invalid = serial_reader_esp32.invalid_packets
                if valid > 0:
                    error_rate = (invalid / (valid + invalid)) * 100
                    print(f"ESP32: {valid} paquetes validos, "
                          f"{invalid} invalidos ({error_rate:.2f}% error)")

        stats_thread = threading.Thread(target=print_stats, daemon=True)
        stats_thread.start()

        # PyQt Application
        app = QApplication(sys.argv)
        window = MainWindow(data_manager, serial_reader_esp32, serial_reader_arduino)
        window.show()

        print("Abriendo ventana de visualizacion...\n")
        print("INSTRUCCIONES:")
        print("   • Usar botones para cambiar derivaciones manualmente\n")

        sys.exit(app.exec())

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