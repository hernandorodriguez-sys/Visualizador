# Configuration file for ECG Monitor Application

# Serial port configurations
SERIAL_PORT_ESP32 = "COM8"
SERIAL_PORT_ARDUINO = "COM1"
BAUD_RATE = 115200

# Debug mode
DEBUG_MODE = False

# Sampling and display configurations
SAMPLE_RATE = 2000
WINDOW_SIZE = 1500
Y_MIN = -0.5
Y_MAX = 2
refresh_interval = 20
buffer_size = 3000

# Peak detection parameters
MIN_PEAK_HEIGHT = 0.05
MIN_PEAK_DISTANCE = 50
PEAK_WIDTH_MIN = 3
PEAK_PROMINENCE = 0.02

# Post-R marker configuration
POST_R_DELAY_MS = 20
POST_R_DELAY_SAMPLES = int((POST_R_DELAY_MS / 1000) * SAMPLE_RATE)

# Lead configurations
LEADS = ["DI", "DII", "DIII", "aVR"]