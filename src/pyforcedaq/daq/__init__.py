__author__ = "Oliver Lindemann"

from abc import ABC, abstractmethod
from typing import Tuple

import numpy.typing as npt

from .._lib.settings import DAQConfiguration


class DAQReadAnalogABC(ABC):
    """Abstract base class for DAQ analog reading."""

    @abstractmethod
    def __init__(self,
                 configuration: DAQConfiguration,
                 read_array_size_in_samples: int):
        """Initialize the DAQ device."""
        pass

    @property
    @abstractmethod
    def is_acquiring_data(self) -> bool:
        """Return whether data acquisition is in progress."""
        pass


    @abstractmethod
    def start_data_acquisition(self) -> None:
        """Start data acquisition."""
        pass

    @abstractmethod
    def stop_data_acquisition(self) -> None:
        """Stop data acquisition."""
        pass

    @abstractmethod
    def read_analog(self) -> Tuple[npt.NDArray, int]:
        """Read analog data.

        Returns
        -------
        read_buffer : numpy array
            The read data.
        read_samples : int
            The number of samples actually read.
        """
        pass


class CalibrationConverterABC(ABC):
    """Abstract base class for Calibration Converters."""

    @abstractmethod
    def __init__(self, calibration_file: str):
        """Initialize the calibration converter with a calibration file."""
        pass

    @abstractmethod
    def convertToFT(self, voltages: npt.NDArray) -> list:
        """Convert voltages to force and torque values."""
        pass

    @abstractmethod
    def bias(self, bias_values: npt.NDArray) -> None:
        """Set the bias for the calibration."""
        pass
