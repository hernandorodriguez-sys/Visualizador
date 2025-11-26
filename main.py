import time
import threading
import sys
from PyQt6.QtWidgets import QApplication

from visualizador.config import SERIAL_PORT_ESP32, SERIAL_PORT_ARDUINO, BAUD_RATE
from visualizador.adc_service import ADCService
from visualizador.ui_service import UIService

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

    # Initialize services
    adc_service = ADCService()
    ui_service = UIService()

    # Connect services
    adc_service.set_services(ui_service)

    # Start services
    adc_service.start()
    ui_service.start(adc_service)

    try:
        print("🚀 Iniciando servicios...\n")

        print("Servicios iniciados:")
        print("   -> ADC Service: ESP32 y Arduino")
        print("   -> UI Service: Interfaz gráfica\n")

        def print_stats():
            while adc_service.running:
                time.sleep(10)
                valid = adc_service.esp32_reader.valid_packets if hasattr(adc_service.esp32_reader, 'valid_packets') else 0
                invalid = adc_service.esp32_reader.invalid_packets if hasattr(adc_service.esp32_reader, 'invalid_packets') else 0
                if valid > 0:
                    error_rate = (invalid / (valid + invalid)) * 100
                    print(f"ESP32: {valid} paquetes validos, "
                          f"{invalid} invalidos ({error_rate:.2f}% error)")

        stats_thread = threading.Thread(target=print_stats, daemon=True)
        stats_thread.start()

        print("Abriendo ventana de visualizacion...\n")
        print("INSTRUCCIONES:")
        print("   • Usar botones para cambiar derivaciones manualmente\n")

        # Run the UI service (blocking)
        ui_service.run_app()

    except KeyboardInterrupt:
        print("\nInterrupcion por teclado - Cerrando...")
    except Exception as e:
        print(f"Error critico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCerrando servicios...")
        adc_service.stop()
        ui_service.stop()
        print("Aplicacion cerrada correctamente")

if __name__ == "__main__":
    main()