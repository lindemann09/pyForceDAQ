DAQ_TYPE = 1 # default to nidaqmx, use daq.MOCK_SENSOR for mock sensor, daq.PYDAQMX for PyDAQmx
USE_AIFTT = True # <-- change to False to use ATI DLL for calibration conversion, otherwise use atiiaftt

SETTINGS_FILE_EXTENSION = ".settings.toml"
DEFAULT_SETTINGS_FILE = "pyForceDAQ" + SETTINGS_FILE_EXTENSION
DEFAULT_OUTPUT_FILENAME = None
CALIBRATION_FOLDER = "calibration"
DATA_FOLDER = "data"
