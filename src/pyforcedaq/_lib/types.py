__author__ = "Oliver Lindemann"

import ctypes as ct

import numpy as np
from numpy.typing import NDArray

from .clock import local_clock
from .misc import MinMaxDetector as _MinMaxDetector

# tag in data output
TAG_COMMENTS = "#"
TAG_DAQEVENT = TAG_COMMENTS + "T"
TAG_UDPDATA = TAG_COMMENTS + "UDP"

CTYPE_FORCES = ct.c_double * 600
CTYPE_TRIGGER = ct.c_double * 2


class PollingPriority(object):  # TODO needed?
    NORMAL = "normal"
    HIGH = "high"
    REALTIME = "real_time"

    @staticmethod
    def get_priority(priority_str):
        """returns normal or the higher priority if detected"""
        if isinstance(priority_str, str):
            if priority_str.find("real") >= 0 and priority_str.find("time") >= 0:
                return PollingPriority.REALTIME
            elif priority_str.startswith("high"):
                return PollingPriority.HIGH

        return PollingPriority.NORMAL


class CTypesForceSensorData(ct.Structure):
    _fields_ = [
        ("sensor_id", ct.c_int),
        ("time", ct.c_int),
        ("forces", CTYPE_FORCES),
        ("trigger", CTYPE_TRIGGER),
    ]


class TimedData(object):
    """The MetaClass TimedData class
    Timestamped data container for force sensor data, UDP data and DAQ events
    """

    def __init__(self, time: float | None):
        if time is None:
            self.time = local_clock()
        else:
            self.time = time


class ForceSensorData(TimedData):
    """The Force data structure with the following properties
    * sensor_id (int)
    * time (time stamp)
    * aquisition delay (time it took to receive the new data)
    * Fx,  Fy, & Fz
    * Tx, Ty, & Tz
    * trigger1 & trigger2

    """

    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    # FIXME update docu, types have change to numpy

    def __init__(
        self,
        time: float | None = None,
        forces: NDArray[np.float64] = np.zeros(6),
        trigger: NDArray[np.float64] = np.zeros(2),
        sensor_id: int = 0,
        trigger_threshold:float =0.9,
        reverse=(),
    ):
        """Create a ForceSensorData object
        Parameters
        ----------
        sensor_id: int, optional
            the id of the sensor device
        time: float, optional
            the timestamp
        forces: array of six floats
            array of the force data defined as [Fx, Fy, Fz, Tx, Ty, Tz]
        trigger: array of two floats
            two trigger values: [trigger1, trigger2]

        trigger_threshold: float (default = 0.4)
            if abs(trigger1/2) < trigger_threshold the threshold it will considered as noise
            and set to zero

        """

        super().__init__(time)
        self.sensor_id = sensor_id
        self.forces = np.asarray(forces, dtype=np.float64)
        self.trigger = np.asarray(trigger, dtype=np.float64)
        if abs(self.trigger[0]) < trigger_threshold:
            self.trigger[0] = 0
        if abs(self.trigger[1]) < trigger_threshold:
            self.trigger[1] = 0
        for r in reverse:
            forces[r] = -1 * forces[r]

    def __str__(self):
        """converts data to string."""
        txt = (
            f"{self.sensor_id:d},{self.time:.5f},{self.forces[0]:.4f},"
            f"{self.forces[1]:.4f},{self.forces[2]:.4f},{self.forces[3]:.4f},"
            f"{self.forces[4]:.4f},{self.forces[5]:.4f}"
        )
        txt += f",{self.trigger[0]:.4f},{self.trigger[1]:.4f}"
        return txt

    @property
    def Fx(self):
        return self.forces[0]

    @Fx.setter
    def Fx(self, value):
        self.forces[0] = value

    @property
    def Fy(self):
        return self.forces[1]

    @Fy.setter
    def Fy(self, value):
        self.forces[1] = value

    @property
    def Fz(self):
        return self.forces[2]

    @Fz.setter
    def Fz(self, value):
        self.forces[2] = value

    @property
    def Tx(self):
        return self.forces[3]

    @Tx.setter
    def Tx(self, value):
        self.forces[3] = value

    @property
    def Ty(self):
        return self.forces[4]

    @Ty.setter
    def Ty(self, value):
        self.forces[4] = value

    @property
    def Tz(self):
        return self.forces[5]

    @Tz.setter
    def Tz(self, value):
        self.forces[5] = value

    @property
    def ctypes_struct(self):
        return CTypesForceSensorData(
            self.sensor_id,
            self.time,
            CTYPE_FORCES(*self.forces.tolist()),
            CTYPE_TRIGGER(*self.trigger.tolist()),
        )

    @ctypes_struct.setter
    def ctypes_struct(self, struct):
        self.sensor_id = struct.sensor_id
        self.time = struct.time
        self.forces = struct.forces
        self.trigger = struct.trigger


class UDPData(TimedData):
    """The UDP data class, used to store UDP DATA with timestamps"""

    def __init__(self, time: float | None, string: str | bytes):
        """Create a UDA_DATA object

        Parameters
        ----------
        time : float
        code : numerical or string

        """
        super().__init__(time)
        if isinstance(string, str):
            self.byte_string = string.encode()
        else:
            self.byte_string = string

    @property
    def unicode(self):
        return self.byte_string.decode("utf-8", "replace")

    def startswith(self, byte_string):
        return self.byte_string[: len(byte_string)] == byte_string


def bytes_startswith(a, b):
    return a[: len(b)] == b


class DAQEvents(TimedData):
    """The DAQEvents data class, used to store trigger

    See Also
    --------
    DataRecorder.set_daq_event()

    """

    def __init__(self, time: float | None, code: str | int | float):
        """Create a DAQEvents object

        Parameters
        ----------
        time : float
        code : numerical or string

        """
        super().__init__(time)
        self.code = code


class Thresholds(object):
    def __init__(self, thresholds, n_channels=1):
        """Thresholds for a one or multiple channels of data"""
        self._thresholds = list(thresholds)
        self._thresholds.sort()
        self.set_number_of_channels(n_channels=n_channels)

    def is_detecting(self, channels=0):
        return (
            self._minmax[channels] is not None or self._prev_level[channels] is not None
        )

    def is_level_change_detecting(self, channels=0):
        return self._prev_level[channels] is not None

    def is_response_minmax_detecting(self, channels=0):
        return self._minmax[channels] is not None

    def is_detecting_anything(self):
        """is detecting something in at least one channel"""
        nn = lambda x: x is not None
        return (
            len(list(filter(nn, self._prev_level))) > 0
            or len(list(filter(nn, self._minmax))) > 0
        )

    def set_number_of_channels(self, n_channels):
        self._prev_level = [None] * n_channels
        self._minmax = [None] * n_channels

    @property
    def thresholds(self):
        return self._thresholds

    def get_level(self, value):
        """return [int]
        int: the level of current sensor value depending of thresholds (array)

        return:
                0 below smallest threshold
                1 large first but small second threshold
                ..
                x larger highest threshold (x=n thresholds)
        """

        level = None
        cnt = 0
        for cnt, x in enumerate(self._thresholds):
            if value < x:
                level = cnt
                break

        if level is None:
            level = cnt + 1
        return level

    def set_level_change_detection(self, value, channel=0):
        """sets level change detection
        returns: current level
        """
        self._prev_level[channel] = self.get_level(value)
        self._minmax[channel] = None
        return self._prev_level[channel]

    def get_level_change(self, value, channel=0):
        """return tuple with level_change (boolean) and current level (int)
        if level change detection is switch on

        Note: after detected level change detection is switched off!
        """

        if self._prev_level[channel] is None:
            return None, None

        current = self.get_level(value)
        changed = current != self._prev_level[channel]
        if changed:
            self._prev_level[channel] = None
        return changed, current

    def __str__(self):
        return str(self._thresholds)

    def set_response_minmax_detection(self, value, duration, channel=0):
        """Start response detection
        Parameters detects minimum and maximum of the response
            after first level change (length =number_of_samples)

        value: start level
        polled samples need to feed via get_response_minmax()

        returns: current level
        """

        lv = self.get_level(value)
        self._minmax[channel] = _MinMaxDetector(start_value=lv, duration_ms=duration)
        self._prev_level[channel] = None
        return lv

    def get_response_minmax(self, value, channel=0):
        """checks for response minimum and maximum if set_response_minmax_detection is switch on
        With this function you add a sample and check if the response can be classified. If so,
        it returns a tuple with the minimum and maximum response level during the response period
        otherwise
            returns None

        tuple with level_change (boolean) and current level (int)

        Note: after response minmax has been determined once response_minmax_detection is switched off!
        """

        if self._minmax[channel] is None:
            return None

        rtn = self._minmax[channel].process(self.get_level(value))
        if rtn is not None:
            # minmax just detected
            self._minmax[channel] = None  # switch off
        return rtn
