# ECG Monitor Visualizer

A real-time ECG monitoring system that reads data from ESP32 and Arduino devices via serial communication, processes ECG signals, detects R-peaks, and provides interactive visualization.

## Features

- **Real-time ECG Monitoring**: Continuous acquisition from ESP32 ADC with PyQt UI
- **Thread-safe Plotting**: Safe realtime plotting using PyQt threads
- **ADC Raw Signal Display**: Direct visualization of raw ADC data
- **Manual Lead Control**: Switch between ECG leads (DI, DII, DIII, aVR)
- **Energy Monitoring**: Track capacitor discharge energy from Arduino
- **Data Logging**: Automatic CSV export of all measurements
- **Info Panel**: Real-time status and energy information display

## Installation

### Prerequisites

- Python 3.14+
- ESP32 device with ECG acquisition firmware
- Arduino device with energy monitoring firmware

### Install Dependencies

Using uv (recommended):
```bash
uv sync
```

See [SETUP.md](SETUP.md) for detailed uv installation and setup instructions.

Or using pip:
```bash
pip install -r requirements.txt
```

## Hardware Setup

1. **ESP32 Connection**: Connect ESP32 to COM7 (configurable)
2. **Arduino Connection**: Connect Arduino to COM8 (configurable)
3. **ECG Electrodes**: Connect ECG leads to ESP32 ADC pins
4. **Energy Circuit**: Connect capacitor discharge circuit to Arduino

## Usage

### Basic Usage

```bash
uv run python main.py
```

See [SETUP.md](SETUP.md) for detailed execution instructions using uv.

### Configuration

Edit `src/visualizador/config.py` to adjust:

- Serial port settings
- Sampling rates
- Peak detection parameters
- Plot display options

### Controls

- **Lead Buttons**: Click DI/DII/DIII/aVR to switch ECG leads
- **Manual Control**: Use buttons for capacitor charge/discharge (via Arduino)
- **Visualization**: Real-time ADC raw signal plot in PyQt window
- **Info Panel**: Bottom panel shows connection status, energies, and discharge info

## Project Structure

```
visualizador/
├── src/
│   └── visualizador/
│       ├── __init__.py
│       ├── config.py          # Configuration parameters
│       ├── data_manager.py    # Thread-safe data management
│       ├── filters.py         # Signal processing filters
│       ├── plot_utils.py      # Matplotlib plotting utilities
│       ├── serial_readers.py  # Serial communication
│       ├── ui_main.py         # PyQt main window
│       └── utils.py           # Utility functions
├── tests/
│   ├── __init__.py
│   └── test_filters.py    # Unit tests
├── docs/
│   └── api.md             # API documentation
├── SETUP.md               # Detailed setup guide
├── main.py                # Entry point
├── pyproject.toml         # Project configuration
└── README.md
```

## API Documentation

See [docs/api.md](docs/api.md) for detailed API reference.

## Testing

Run tests with:
```bash
uv run python -m pytest tests/
```

## Development

### Adding New Features

1. Add code to appropriate module in `src/visualizador/`
2. Update imports in `__init__.py` if exposing new functionality
3. Add tests in `tests/`
4. Update documentation

### Code Style

- Follow PEP 8 conventions
- Use type hints where possible
- Add docstrings to functions and classes

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- Built with PyQt6 for the user interface
- Matplotlib for real-time plotting within PyQt
- Uses scipy for signal processing
- Serial communication via pyserial