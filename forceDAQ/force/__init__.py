"""
import this package contains  all relevant classes and function to
program your force sensor
"""

__author__ = 'Oliver Lindemann'

from . import _log
from .data_recorder import DataRecorder
from .sensor import Sensor, SensorSettings
from .sensor_process import SensorProcess

_log.set_logging(data_directory="data", log_file="recording.log")
