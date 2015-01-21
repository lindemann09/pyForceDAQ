__author__ = 'Oliver Lindemann'

import ctypes as ct

CTYPE_FORCES = ct.c_float * 600
CTYPE_TRIGGER = ct.c_float * 2

class CTypesForceData(ct.Structure):
    _fields_ = [("device_id", ct.c_int),
            ("time", ct.c_int),
            ("forces", CTYPE_FORCES),
            ("trigger", CTYPE_TRIGGER)]


class ForceData(object):
    """The Force data structure with the following properties
        * device_id
        * Fx,  Fy, & Fz
        * Tx, Ty, & Tz
        * trigger1 & trigger2
        * time

    """

    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    str_variable_names = "device_id, time, Fx, Fy, Fz, Tx, Ty, Tz, " + \
                     "trigger1, trigger2"

    def __init__(self, time=0, forces=[0] * 6, trigger=(0, 0),
                 device_id=0):
        """Create a ForceData object
        Parameters
        ----------
        device_id: int, optional
            the id of the sensor device
        time: int, optional
            the timestamp
        forces: array of six floats
            array of the force data defined as [Fx, Fy, Fz, Tx, Ty, Tz]
        trigger: array of two floats
            two trigger values: [trigger1, trigger2]

        """

        self.time = time
        self.device_id = device_id
        self.forces = forces
        self.trigger = trigger

    def __str__(self):
        """converts data to string. """
        txt = "%d,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (self.device_id,
                                                           self.time,
                                                           self.forces[0],
                                                           self.forces[1],
                                                           self.forces[2],
                                                           self.forces[3],
                                                           self.forces[4],
                                                           self.forces[5])
        txt += ",%.4f,%.4f" % (self.trigger[0], self.trigger[1])
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
        return self.forces[3]

    @Tz.setter
    def Tz(self, value):
        self.forces[3] = value

    @property
    def ctypes_struct(self):
        return CTypesForceData(self.device_id, self.time,
              CTYPE_FORCES(*self.forces), CTYPE_TRIGGER(*self.trigger))

    @ctypes_struct.setter
    def ctypes_struct(self, struct):
        self.device_id = struct.device_id
        self.time = struct.time
        self.force = struct.forces
        self.trigger = struct.triger



class UDPData(object):
    """The UDP data class, used to store UDP DATA with timestamps

    """

    def __init__(self, string, time):
        """Create a UDA_DATA object

        Parameters
        ----------
        time : int
        code : numerical or string

        """
        self.time = time
        self.string = string



class SoftTrigger(object):
    """The SoftTrigger data class, used to store trigger

    See Also
    --------
    DataRecorder.set_soft_trigger()

    """

    def __init__(self, time, code):
        """Create a SoftTrigger object

        Parameters
        ----------
        time : int
        code : numerical or string

        """
        self.time = time
        self.code = code

