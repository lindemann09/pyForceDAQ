__author__ = "Oliver Lindemann"

import ctypes as ct

import numpy as np
from numpy.typing import NDArray

from ..tools.clock import local_clock

# tag in data output
TAG_COMMENTS = "#"

CTYPE_FORCES = ct.c_double * 600
CTYPE_TRIGGER = ct.c_double * 2


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
    n_forces = 6
    n_triggers = 2
    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

    # FIXME update docu, types have change to numpy

    def __init__(
        self,
        forces: NDArray[np.float64],
        trigger: NDArray[np.float64] = np.zeros(2),
        time: float | None = None,
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
        assert len(forces) == ForceSensorData.n_forces

        self.trigger = np.asarray(trigger, dtype=np.float64)
        if abs(self.trigger[0]) < trigger_threshold:
            self.trigger[0] = 0
        if abs(self.trigger[1]) < trigger_threshold:
            self.trigger[1] = 0
        for r in reverse:
            forces[r] = -1 * forces[r]

    def csv(self,
            write_device_id: bool,
            write_forces: list[bool],
            write_trigger: list[bool],
            float_decimal_places: int= 4) -> str:
        """converts data to string."""

        float_format = "{0:." + str(float_decimal_places) + "f},"
        txt = f"{self.time},"
        if write_device_id:
            txt += f"{self.sensor_id},"
        for x in self.forces[write_forces]:
            txt += float_format.format(x)
        for x in self.trigger[write_trigger]:
            if isinstance(x, int):
                txt += f"{x},"
            else:
                txt += float_format.format(x)
        return txt[:-1]


    def __str__(self):
        return self.csv(write_device_id=True,
                        write_forces=[True]*ForceSensorData.n_forces,
                        write_trigger=[True]*ForceSensorData.n_triggers,
                        float_decimal_places=4)

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

    @classmethod
    def force_id(cls, force_label) -> int | None:
        """returns the id of the force parameter with the given label or None if not found"""
        try:
            return cls.forces_names.index(force_label)
        except ValueError:
            return None

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
        return self.byte_string.decode("utf-8", "replace")  # pyright: ignore[reportAttributeAccessIssue]

    def startswith(self, byte_string):
        return self.byte_string[: len(byte_string)] == byte_string


