from .timer import get_time


def N2g(N):
    kg = N/9.81
    return kg*1000

class MinMaxDetector(object):

    def __init__(self, start_value, duration):
        self._minmax = [start_value, start_value]
        self._duration_in_sec = float(duration) / 1000
        self._level_change_time = None

    def process(self, value):
        """Returns minmax (tuple) for a number of samples after the first
        level change has occurred, otherwise None"""

        if self._level_change_time is not None:
            if (get_time() - self._level_change_time) >= self._duration_in_sec:
                return tuple(self._minmax)

            if value > self._minmax[1]:
                self._minmax[1] = value
            elif value < self._minmax[0]:
                self._minmax[0] = value

        elif self._minmax[0] != value: # level change just occurred
            self._level_change_time = get_time()
            return self.process(value)

        return None

    @property
    def is_sampling_for_minmax(self):
        """true true if currently sampling for minmax"""
        return (self._level_change_time is not None) and \
               (get_time() - self._level_change_time) < self._duration_in_sec
