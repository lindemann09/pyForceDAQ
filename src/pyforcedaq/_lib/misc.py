import logging
import os
import sys
from pathlib import Path

from ..constants import SETTINGS_FILE_EXTENSION
from .clock import local_clock_ms


def set_logging(data_directory, log_file):
    base_dir = os.path.split(sys.argv[0])[0]
    log_dir = os.path.join(base_dir, data_directory)
    try:
        os.mkdir(log_dir)
    except:
        pass
    log_file = os.path.abspath(os.path.join(log_dir, log_file))
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%m-%d %H:%M:%S",
        filename=log_file,
        filemode="a",
    )
    return log_file


def list_settings_files():
    """Returns a list of all settings files in the current directory."""
    return [f.name for f in Path(".").glob(f"*{SETTINGS_FILE_EXTENSION}")]


def N2g(N):
    kg = N / 9.81
    return kg * 1000


class MinMaxDetector(object):
    def __init__(self, start_value, duration_ms):
        self._minmax = [start_value, start_value]
        self._duration_ms = duration_ms
        self._level_change_time = None

    def process(self, value):
        """Returns minmax (tuple) for a number of samples after the first
        level change has occurred, otherwise None"""

        if self._level_change_time is not None:
            if (local_clock_ms() - self._level_change_time) >= self._duration_ms:
                return tuple(self._minmax)

            if value > self._minmax[1]:
                self._minmax[1] = value
            elif value < self._minmax[0]:
                self._minmax[0] = value

        elif self._minmax[0] != value:  # level change just occurred
            self._level_change_time = local_clock_ms()
            return self.process(value)

        return None

    @property
    def is_sampling_for_minmax(self):
        """true true if currently sampling for minmax"""
        return (self._level_change_time is not None) and (
            local_clock_ms() - self._level_change_time
        ) < self._duration_ms


# def find_calibration_file(calibration_folder: str, device_label: str,
#                           calibration_suffix=".cal") -> str:

#     needle = 'Serial="{0}"'.format(device_label)
#     calibration_files = []
#     for x in listdir(path.abspath(calibration_folder)):
#         filename = path.join(calibration_folder, x)
#         if path.isfile(filename) and filename.endswith(calibration_suffix):
#             with open(filename, "r") as fl:
#                 for l in fl:
#                     if l.find(needle)>0:
#                         print("Found calibration file for sensor '{0}' : {1}.".format(
#                             device_label, filename))
#                         calibration_files.append(filename)

#     if len(calibration_files) == 1:
#         return calibration_files[0]
#     elif len(calibration_files) > 1:
#         print("Multiple calibration files found for sensor '{0}'".format(device_label))
#         for f in calibration_files:
#             print("  - {0}".format(f))
#         print("Please ensure that only one calibration file exists for each sensor")
#     else:
#         print("No calibration file found for sensor '{0}'.".format(device_label))
#     exit()


# Sensor History with moving average filtering and distance, velocity
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
            self.moving_average = list(
                map(
                    lambda x: x[0] + (float(x[1] - x[2]) / len(self.history)),
                    zip(self.moving_average, values, pop),
                )
            )

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
