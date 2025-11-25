# Setup Guide for ECG Monitor Visualizer

This guide provides detailed instructions for setting up and running the ECG Monitor Visualizer using `uv` for dependency management and execution.

## Prerequisites

- **Python 3.14+**: Ensure you have Python 3.14 or higher installed
- **uv**: A fast Python package installer and resolver
- **Hardware**:
  - ESP32 device with ECG acquisition firmware
  - Arduino device with energy monitoring firmware
  - Serial ports (default: COM7 for ESP32, COM8 for Arduino)

## Installing uv

If you don't have `uv` installed, install it using the official installer:

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Alternative Installation Methods
See the [uv installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for other installation options.

## Project Setup

1. **Clone or download the project**:
   ```bash
   git clone <repository-url>
   cd visualizador
   ```

2. **Sync dependencies with uv**:
   ```bash
   uv sync
   ```

   This command will:
   - Read `pyproject.toml` for project configuration
   - Resolve and install all dependencies (matplotlib, numpy, pyserial, scipy, PyQt6)
   - Create a virtual environment if one doesn't exist
   - Install the project in editable mode

3. **Verify installation**:
   ```bash
   uv run python --version
   uv run python -c "import PyQt6, matplotlib, numpy, serial, scipy; print('All dependencies installed successfully')"
   ```

## Running the Application

### Using uv run

Always use `uv run` to execute commands within the project's virtual environment:

```bash
uv run python main.py
```

This ensures that:
- The correct Python interpreter is used
- All dependencies are available
- The project modules can be imported

### Alternative Execution Methods

While `uv run` is recommended, you can also:

1. **Activate the virtual environment manually**:
   ```bash
   uv shell
   python main.py
   ```

2. **Use uv run with other commands**:
   ```bash
   # Run tests
   uv run python -m pytest tests/

   # Run with specific Python version
   uv run --python 3.14 python main.py
   ```

## Configuration

Before running, ensure your hardware is connected and configured:

1. **ESP32**: Connected to COM7 (or update `src/visualizador/config.py`)
2. **Arduino**: Connected to COM8 (or update `src/visualizador/config.py`)
3. **ECG Electrodes**: Properly connected to ESP32 ADC pins
4. **Energy Circuit**: Capacitor discharge circuit connected to Arduino

## Troubleshooting

### Common Issues

1. **Serial Port Not Found**:
   - Check device manager for correct COM ports
   - Update `SERIAL_PORT_ESP32` and `SERIAL_PORT_ARDUINO` in `config.py`

2. **PyQt6 Import Error**:
   - Ensure `uv sync` completed successfully
   - Try reinstalling: `uv sync --reinstall`

3. **Permission Denied on Serial Ports**:
   - Run terminal as administrator (Windows)
   - Ensure no other programs are using the serial ports

4. **Virtual Environment Issues**:
   - Delete `.venv` folder and run `uv sync` again
   - Check Python version compatibility

### Verifying Setup

Run these commands to verify everything is working:

```bash
# Check uv version
uv --version

# Check Python in virtual environment
uv run python --version

# Test imports
uv run python -c "
import sys
print(f'Python: {sys.version}')
import PyQt6
print('PyQt6: OK')
import matplotlib
print('matplotlib: OK')
import numpy
print('numpy: OK')
import serial
print('pyserial: OK')
import scipy
print('scipy: OK')
print('All dependencies verified!')
"

# Test project imports
uv run python -c "
from visualizador.config import SERIAL_PORT_ESP32, SERIAL_PORT_ARDUINO
from visualizador.data_manager import DataManager
from visualizador.ui_main import MainWindow
print('Project imports: OK')
"
```

## Development Workflow

When working on the project:

1. **Sync after dependency changes**:
   ```bash
   uv sync
   ```

2. **Run the application**:
   ```bash
   uv run python main.py
   ```

3. **Run tests**:
   ```bash
   uv run python -m pytest tests/
   ```

4. **Add new dependencies**:
   - Edit `pyproject.toml`
   - Run `uv sync`

## Updating Dependencies

To update all dependencies to their latest compatible versions:

```bash
uv sync --upgrade
```

To update a specific package:

```bash
uv sync --upgrade-package <package-name>
```

## Project Structure

After setup, your project should look like:

```
visualizador/
├── .venv/                 # Virtual environment (created by uv)
├── src/
│   └── visualizador/
│       ├── ui_main.py     # PyQt main window
│       ├── plot_utils.py  # Matplotlib plotting
│       ├── config.py      # Configuration
│       └── ...
├── pyproject.toml         # Project configuration
├── uv.lock               # Lock file with exact versions
└── README.md
```

## Next Steps

Once setup is complete:

1. Connect your ESP32 and Arduino devices
2. Run `uv run python main.py`
3. The PyQt application window will open with real-time ECG visualization
4. Use the buttons to switch between ECG leads
5. Monitor the info panel for connection status and energy readings

For more information, see the main [README.md](README.md) file.