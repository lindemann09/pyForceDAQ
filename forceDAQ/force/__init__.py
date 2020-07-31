"""
import this package contains  all relevant classes and function to
program your own force
"""

__author__ = 'Oliver Lindemann'

from .data_recorder import DataRecorder
from .sensor import SensorSettings, Sensor
from .sensor_process import SensorProcess

from . import _log
_log.set_logging(data_directory="data", log_file="recording.log")
