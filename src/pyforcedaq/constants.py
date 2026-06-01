NIDAQMX = 1
PYDAQMX = 2
MOCK_SENSOR = 9

DAQ_TYPE = NIDAQMX # default to nidaqmx, use constants.MOCK_SENSOR for mock sensor, constants.PYDAQMX for PyDAQmx
USE_AIFTT = True # <-- change to False to use ATI DLL for calibration conversion, otherwise use atiiaftt

SETTINGS_FILE_EXTENSION = ".settings.toml"
DEFAULT_SETTINGS_FILE = "pyForceDAQ" + SETTINGS_FILE_EXTENSION
DEFAULT_OUTPUT_FILENAME = None
CALIBRATION_FOLDER = "calibration"
DATA_FOLDER = "data"
