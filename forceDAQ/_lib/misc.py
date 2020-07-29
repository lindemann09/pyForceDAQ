from .timer import get_time_ms
from os import listdir, path

def N2g(N):
    kg = N/9.81
    return kg*1000

class MinMaxDetector(object):

    def __init__(self, start_value, duration):
        self._minmax = [start_value, start_value]
        self._duration = duration
        self._level_change_time = None

    def process(self, value):
        """Returns minmax (tuple) for a number of samples after the first
        level change has occurred, otherwise None"""

        if self._level_change_time is not None:
            if (get_time_ms() - self._level_change_time) >= self._duration:
                return tuple(self._minmax)

            if value > self._minmax[1]:
                self._minmax[1] = value
            elif value < self._minmax[0]:
                self._minmax[0] = value

        elif self._minmax[0] != value: # level change just occurred
            self._level_change_time = get_time_ms()
            return self.process(value)

        return None

    @property
    def is_sampling_for_minmax(self):
        """true true if currently sampling for minmax"""
        return (self._level_change_time is not None) and \
               (get_time_ms() - self._level_change_time) < self._duration

def find_calibration_file(calibration_folder, sensor_name,
                          calibration_suffix=".cal"):

    needle = 'Serial="{0}"'.format(sensor_name)
    for x in listdir(path.abspath(calibration_folder)):
        filename = path.join(calibration_folder, x)
        if path.isfile(filename) and filename.endswith(calibration_suffix):
            with open(filename, "r") as fl:
                for l in fl:
                    if l.find(needle)>0:
                        return filename

    raise RuntimeError("Can't find calibration file for sensor '{0}'.".format(sensor_name))

