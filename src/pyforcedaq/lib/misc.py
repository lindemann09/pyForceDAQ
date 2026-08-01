import logging
import os
import socket
from pathlib import Path
from subprocess import check_output

import appdirs
import numpy as np
from numpy import typing as npt

from .clock import local_clock_ms


def set_logging(log_file):
    log_dir = Path(appdirs.AppDirs("").user_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file
    logging.basicConfig(filename=log_file,
                        encoding='utf-8',
                        format="[%(asctime)s] %(levelname)s: %(message)s",
                        datefmt="%m%d %H:%M:%S",
                        level=logging.INFO)
    return log_file



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

def get_lan_ip():
    if os.name == "nt":
        # Windows
        return socket.gethostbyname(socket.gethostname())
    else:
        # Linux and macOS
        try:
            # Try Linux command first
            rtn = check_output(["hostname", "-I"]).decode().strip()
            return rtn.split()[0] if rtn else None
        except:
            try:
                # Fallback to macOS command
                rtn = check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
                return rtn if rtn else None
            except:
                # Fallback to socket method if both commands fail
                return socket.gethostbyname(socket.gethostname())




# Sensor History with moving average filtering and distance, velocity
class SensorHistory(object):
    """The Sensory History keeps track of the last n recorded sample and
    calculates online the moving average (running mean).

    SensorHistory.moving_average

    """

    def __init__(self, history_size, number_of_parameter):
        self.history = [np.zeros(number_of_parameter, dtype=np.float64) for _ in range(history_size)]

    def __str__(self):
        return str(self.history)

    def update(self, values):
        """Update history and calculate moving average

        (correct for accumulated rounding errors ever 10000 samples)

        Parameter
        ---------
        values : list of values for all sensor parameters

        """

        self.history.pop(0)
        self.history.append(values)

    def moving_averages(self) -> npt.NDArray[np.floating]:
        """Returns a list of moving averages for all sensor parameters."""
        return np.mean(self.history, axis=0)

    def moving_average(self, sensor:int) -> np.floating:
        """Returns the moving average for a specific sensor parameter."""
        return np.mean([x[sensor] for x in self.history])

    @property
    def history_size(self):
        return len(self.history)

    @property
    def number_of_parameter(self):
        return len(self.history[0])