__author__ = "Oliver Lindemann"
__version__ = "0.5"

from .. import USE_MOCK_SENSOR
from ._pyATIDAQ import ATI_CDLL
from .config import DAQConfiguration

if USE_MOCK_SENSOR:
    print("Using mock sensor instead.")
    from ._mock_sensor import DAQReadAnalog
else:
    #### change import here if you want to use nidaqmx instead of pydaymx ####
    try:
        from ._use_pydaqmx import DAQReadAnalog
        #from ._use_nidaqmx import DAQReadAnalog
    except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
        print("Error importing DAQReadAnalog: {0}".format(e))
        print("Warning: PyDAQmx or nidaqmx not found. Using mock sensor instead.")
        from ._mock_sensor import DAQReadAnalog

