import ctypes as ct
from typing import List

from numpy.typing import NDArray

from ._pyATIDAQ import ATI_CDLL


class CalibrationConverter(object):
    def __init__(self, calibration_file: str):
        self._atidaq = ATI_CDLL()
        self._atidaq.createCalibration(calibration_file, ct.c_short(1))
        self._atidaq.setForceUnits("N")
        self._atidaq.setTorqueUnits("N-m")

    def convertToFT(self, voltages: NDArray):
        return self._atidaq.convertToFT(voltages)

    def bias(self, bias_values: NDArray):
        self._atidaq.bias(bias_values)
