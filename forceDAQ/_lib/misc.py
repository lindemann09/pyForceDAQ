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


"""Sensor History with moving average filtering and distance, velocity"""
class SensorHistory(object):
    """The Sensory History keeps track of the last n recorded sample and
    calculates online the moving average (running mean).

    SensorHistory.moving_average

    """

    def __init__(self, history_size, number_of_parameter):
        self.history = [[0] * number_of_parameter] * history_size
        self.moving_average = [0] * number_of_parameter
        self._correction_cnt = 0
        self._previous_moving_average = self.moving_average

    def __str__(self):
        return str(self.history)

    def update(self, values):
        """Update history and calculate moving average

        (correct for accumulated rounding errors ever 10000 samples)

        Parameter
        ---------
        values : list of values for all sensor parameters

        """

        self._previous_moving_average = self.moving_average
        pop = self.history.pop(0)
        self.history.append(values)
        # pop first element and calc moving average
        if self._correction_cnt > 10000:
            self._correction_cnt = 0
            self.moving_average = self.calc_history_average()
        else:
            self._correction_cnt += 1
            self.moving_average = list(map(
                lambda x: x[0] + (float(x[1] - x[2]) / len(self.history)),
                zip(self.moving_average, values, pop)))


    def calc_history_average(self):
        """Calculate history averages for all sensor parameter.

        The method is more time consuming than calling the property
        `moving_average`. It is does however not suffer from accumulated
        rounding-errors such as moving average.

        """

        s = [float(0)] * self.number_of_parameter
        for t in self.history:
            s = list(map(lambda x: x[0] + x[1], zip(s, t)))
        return list(map(lambda x: x / len(self.history), s))


    @property
    def history_size(self):
        return len(self.history)

    @property
    def number_of_parameter(self):
        return len(self.history[0])

    @property
    def previous_moving_average(self):
        return self._previous_moving_average

