import atiiaftt
from numpy.typing import NDArray

from . import CalibrationConverterABC

print("Using ATI IAFTT for calibration conversion.")

class CalibrationConverter(CalibrationConverterABC):  # type: ignore

    def __init__(self, calibration_file:str):
        self._ftsensor = atiiaftt.FTSensor(calibration_file, index=1)

    def convertToFT(self, voltages:NDArray) -> list:
        return self._ftsensor.convertToFt(voltages.tolist()) # FIXME reverse parameter
        #TODO: to list needed?

    def bias(self, bias_values: NDArray) -> None:
        self._ftsensor.bias(bias_values.tolist())