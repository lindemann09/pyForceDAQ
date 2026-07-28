from enum import Enum


class DaqType(Enum):
    NIDAQMX = 1
    PYDAQMX = 2
    MOCK_SENSOR = 9
    UNDEFINED = 0


DAQ_TYPE = DaqType.UNDEFINED
USE_AIFTT = True # <-- change to False to use ATI DLL for calibration conversion, otherwise use atiiaftt

SETTINGS_FILE_EXTENSION = ".toml"
DEFAULT_SETTINGS_FILE = "pyForceDAQ.settings" + SETTINGS_FILE_EXTENSION
DEFAULT_OUTPUT_FILENAME = None
CALIBRATION_FOLDER = "."
DATA_FOLDER = "data"
