from collections import deque
from copy import copy
from time import perf_counter

import numpy as np
from numpy.typing import NDArray


def N2g(N):
    kg = N / 9.81
    return kg * 1000



class DataBuffer:

    """A buffer for data with a fixed about of parameters and a fixed length.
    The buffer is implemented as a deque. First data append, defined the number of paramters.
    """

    def __init__(self, maxlen: int):
        self.buffer = deque(maxlen=maxlen)
        self._n_para = -1

    @property
    def number_of_parameters(self):

        return self._n_para

    def append(self, values: NDArray | list | tuple| float):
        """Append a new sample to the buffer."""
        if isinstance(values, (np.ndarray, list, tuple)):
            value_size = len(values)
        else:
            value_size = 1

        if self._n_para != value_size:
            if self._n_para == -1:
                # it's the first sample
                self._n_para = value_size
            else:
                raise ValueError(f"DataBuffer: Number of parameters ({value_size}) does not match buffer size ({self._n_para})")

        self.buffer.append(values)

    def get_last(self, n: int) -> NDArray[np.floating]:
        """Returns the last n data points in the buffer as a numpy array."""
        if n > len(self.buffer):
            raise ValueError(f"last n ({n}) is greater than the buffer size ({len(self.buffer)})")
        return np.array(self.buffer)[-n:]

    def buffer_mean(self, last_n: int | None = None) -> NDArray[np.floating]:
        """Returns the mean of the last n data points in the buffer as a numpy array."""

        if isinstance(last_n, int):
            dat = self.get_last(last_n)
        else:
            dat = self.buffer
        return np.atleast_1d(np.mean(dat, axis=0))


class MinMaxDetector:
    """Detects minimum and maximum of a number during a certain period.
    """

    FIRST_SAMPLE = -1
    NEW_MINIMUM = 1
    NEW_MAXIMUM = 2

    def __init__(self):

        self.minimum = None
        self.maximum = None
        self._time_fist_sample = None

    def reset(self):
        self.minimum = None
        self.maximum = None
        self._time_fist_sample = None

    def duration_ms(self) -> int:
        """Returns the duration in milliseconds since the first sample was pushed.
        returns -1 if no sample has been pushed yet.
        """
        if self._time_fist_sample is None:
            return -1
        else:
            return int((perf_counter() - self._time_fist_sample) * 1000)

    def process(self, value) -> int:
        """Returns

            MinMaxDetector.FIRST_SAMPLE = -1 if first sample is pushed, i.e., value=minimum=maximum
            0 if no change, otherwise returns
            MinMaxDetector.NEW_MINIMUM = 1if new minimum detected
            MinMaxDetector.NEW_MAXIMUM = 2 if new maximum detected
        """
        if self._time_fist_sample is None:
            self._time_fist_sample = perf_counter()
            self.minimum = value
            self.maximum = value
            return MinMaxDetector.FIRST_SAMPLE
        elif value > self.maximum:
            self.maximum = value
            return MinMaxDetector.NEW_MAXIMUM
        elif value < self.minimum:
            self.minimum = value
            return MinMaxDetector.NEW_MINIMUM

        return 0

class Thresholds:

    def __init__(self, thresholds: list[float]):
        """Thresholds for a one channels of data"""
        self.thresholds = copy(list(thresholds)) # ensure no np.array
        self.thresholds.sort()
        self._curr_level = None

    @property
    def current_level(self) -> int | None:
        """Returns the current level of the last processed value
        levels:
                0 below smallest threshold
                1 large first but small second threshold
                ..
                x larger highest threshold (x=n thresholds)

                None if no value has been processed yet.
        """
        return self._curr_level


    def reset(self, new_thresholds: list[float] | None = None):
        self._curr_level = None
        if new_thresholds is not None:
            self.thresholds = copy(list(new_thresholds))
            self.thresholds.sort()

    def has_level(self) -> bool:
        """Returns True if the thresholds are set and at least one level has
        been detected via process(), otherwise returns False."""
        return self._curr_level is not None

    def _find_level(self, value: float) -> int:
        """return [int]
        int: the level of current sensor value depending of thresholds
        """

        level = None
        cnt = 0
        for cnt, x in enumerate(self.thresholds):
            if value < x:
                level = cnt
                break

        if level is None:
            level = cnt + 1
        return level

    def process(self, value: float) -> bool:
        """return true if a new level is detected

        Note
        ----
        for levels see property current_level
        """

        lvl = self._find_level(value)
        if lvl != self._curr_level:
            self._curr_level = lvl
            return True
        else:
            return False