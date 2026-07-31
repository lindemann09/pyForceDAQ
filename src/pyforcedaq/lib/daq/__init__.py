__author__ = "Oliver Lindemann"

from abc import ABC, abstractmethod

from numpy import float64
from numpy.typing import NDArray

from ..settings import SensorSettings


class DAQReadAnalogABC(ABC):
    """Abstract base class for DAQ analog reading."""

    @abstractmethod
    def __init__(self,
                 configuration: SensorSettings,
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
    def read_analog(self) -> NDArray[float64]:
        """Read analog data.

        Returns
        -------
        read_buffer : numpy array
            The read data.
        read_samples : int
            The number of samples actually read.
        """
        pass
