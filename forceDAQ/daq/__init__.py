__author__ = "Oliver Lindemann"
__version__ = "0.4"

from .. import USE_MOCK_SENSOR
from ._pyATIDAQ import ATI_CDLL
from .config import DAQConfiguration

if USE_MOCK_SENSOR:
    print("Using mock sensor instead.")
    from ._mock_sensor import DAQReadAnalog
else:
    #### change import here if you want to use nidaqmx instead of pydaymx ####
    try:
        from ._daq_read_analog_pydaqmx import DAQReadAnalog
        #from ._daq_read_analog_nidaqmx import DAQReadAnalog
    except (ImportError, ModuleNotFoundError):
        print("Warning: PyDAQmx or nidaqmx not found. Using mock sensor instead.")
        from ._mock_sensor import DAQReadAnalog

