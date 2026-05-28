USE_MOCK_SENSOR = False # <-- change for usage in lab to False
USE_PYDAQMX = False # <-- change to True to use pyDAQmx instead of nidaqmx, requires pyDAQmx installation
USE_ATI_DLL = False # <-- change to True to use ATI DLL for calibration conversion, otherwise use atiiaftt

SETTINGS_FILE_EXTENSION = ".settings.toml"
DEFAULT_SETTINGS_FILE = "pyForceDAQ" + SETTINGS_FILE_EXTENSION
DEFAULT_OUTPUT_FILENAME = None
CALIBRATION_FOLDER = "calibration"
DATA_FOLDER = "data"
