__author__ = "Oliver Lindemann"
__version__ = "0.6"

from .._lib.constants import USE_ATI_DLL, USE_MOCK_SENSOR, USE_PYDAQMX

if USE_MOCK_SENSOR:
    print("Using mock sensor instead.")
    from ._mock_sensor import DAQReadAnalog

else:
    try:
        if USE_PYDAQMX:
            print("Using PyDAQmx for DAQ access.")
            from ._use_pydaqmx import DAQReadAnalog
        else:
            print("Using nidaqmx for DAQ access.")
            from ._use_nidaqmx import DAQReadAnalog
    except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
        print("Error importing DAQReadAnalog: {0}".format(e))
        print("Warning: PyDAQmx or nidaqmx not found. Using mock sensor instead.")
        from ._mock_sensor import DAQReadAnalog

if not USE_ATI_DLL:
    print("Using ATI IAFTT for calibration conversion.")
    from ._calibration_iaftt import CalibrationConverter

else:
    print("ATI_CDLL for calibration conversion.")
    from ._calibration_dll import CalibrationConverter
