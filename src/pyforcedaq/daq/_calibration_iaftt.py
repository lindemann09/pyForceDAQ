from typing import List

import atiiaftt
from numpy.typing import NDArray


class CalibrationConverter(object):  # type: ignore

    def __init__(self, calibration_file:str):
        self._ftsensor = atiiaftt.FTSensor(calibration_file, index=1)

    def convertToFT(self, voltages:NDArray, reverse_parameters:List[int]):
        return self._ftsensor.convertToFt(voltages.tolist()) # FIXME reverse parameter
        #TODO: to list needed?

    def bias(self, bias_values: NDArray):
        self._ftsensor.bias(bias_values.tolist())