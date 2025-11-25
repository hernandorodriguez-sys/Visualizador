# ECG Monitor Visualizer API Documentation

## Overview

The ECG Monitor Visualizer is a Python package for real-time ECG monitoring using ESP32 and Arduino devices connected via serial ports.

## Main Components

### DataManager

Central data management class that handles thread-safe data storage and processing.

```python
from visualizador import DataManager

data_manager = DataManager()
```

**Key attributes:**
- `voltage_buffer`: Raw ECG voltage data
- `filtered_buffer`: Baseline-filtered ECG data
- `baseline_buffer`: Baseline values
- `esp32_connected`: ESP32 connection status
- `arduino_connected`: Arduino connection status

### Serial Readers

#### SerialReaderESP32

Handles communication with ESP32 device for ECG data acquisition.

```python
from visualizador import SerialReaderESP32

reader = SerialReaderESP32(port="COM7", baud_rate=115200)
reader.start(data_manager)
```

**Methods:**
- `start(data_manager)`: Begin reading data
- `stop()`: Stop reading data
- `send_lead_command(lead)`: Send lead change command

#### SerialReaderArduino

Handles communication with Arduino device for energy monitoring.

```python
from visualizador import SerialReaderArduino

reader = SerialReaderArduino(port="COM8", baud_rate=115200)
reader.start(data_manager)
```

### Filters

#### BaselineEMA

Exponential moving average filter for baseline drift removal.

```python
from visualizador import BaselineEMA

filter_obj = BaselineEMA(alpha=0.995)
filtered_voltage, baseline = filter_obj.process_sample(voltage)
```

### Plot Utilities

#### setup_plot(data_manager, serial_reader_esp32)

Initializes the matplotlib visualization interface.

#### update_plot(frame, ...)

Updates the plot for animation (called by FuncAnimation).

### Utility Functions

#### detect_r_peaks_improved(signal_data)

Detects R-peaks in ECG signal using scipy's find_peaks.

#### init_csv()

Initializes CSV file for data logging.

## Configuration

All configuration parameters are defined in `config.py`:

- Serial ports and baud rates
- Sampling parameters
- Peak detection thresholds
- Plot settings

## Usage Example

```python
from visualizador import (
    DataManager, SerialReaderESP32, SerialReaderArduino,
    setup_plot, init_csv
)

# Initialize components
data_manager = DataManager()
csv_filename, csv_file, csv_writer = init_csv()

esp32_reader = SerialReaderESP32("COM7", 115200)
arduino_reader = SerialReaderArduino("COM8", 115200)

# Setup plot
plot_setup = setup_plot(data_manager, esp32_reader)

# Start readers
esp32_reader.start(data_manager)
arduino_reader.start(data_manager)

# Run visualization (handled by matplotlib)