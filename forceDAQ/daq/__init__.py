__author__ = "Oliver Lindemann"
__version__ = "0.3"

from ._config import DAQConfiguration
from ._pyATIDAQ import ATI_CDLL, find_calibration_file

#### change import here if you want to use nidaqmx instead of pydaymx ####
try:
    from ._daq_read_Analog_pydaqmx import DAQReadAnalog
    # from ..daq.daq_read_analog_nidaqmx import DAQReadAnalog
except:
    from ._daq_read_Analog_dummy import DAQReadAnalog