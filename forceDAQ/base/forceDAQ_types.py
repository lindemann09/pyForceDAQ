__author__ = 'Oliver Lindemann'

import ctypes as ct
from misc import MinMaxDetector

# tag in data output
TAG_COMMENTS = "#"
TAG_SOFTTRIGGER = TAG_COMMENTS + "T"
TAG_UDPDATA = TAG_COMMENTS + "UDP"

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
        * trigger1 & trigger2  (hardware trigger)
        * time

    """

    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

    def __init__(self, time=0, forces=[0] * 6, hardware_trigger=(0, 0),
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
        self.hardware_trigger = hardware_trigger

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
        txt += ",%.4f,%.4f" % (self.hardware_trigger[0], self.hardware_trigger[1])
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
        return CTypesForceData(self.device_id, self.time,
              CTYPE_FORCES(*self.forces), CTYPE_TRIGGER(*self.hardware_trigger))

    @ctypes_struct.setter
    def ctypes_struct(self, struct):
        self.device_id = struct.device_id
        self.time = struct.time
        self.force = struct.forces
        self.hardware_trigger = struct.trigger



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



class DAQEvents(object):
    """The DAQEvents data class, used to store trigger

    See Also
    --------
    DataRecorder.set_soft_trigger()

    """

    def __init__(self, time, code):
        """Create a DAQEvents object

        Parameters
        ----------
        time : int
        code : numerical or string

        """
        self.time = time
        self.code = code


class GUIRemoteControlCommands(object):
    """
    SET_THRESHOLDS needs to be followed by a threshold object
    SET_RESPONSE_MINMAX_DETECTION needs to be followed an integer representing duration of sampling

    feedback:
        CHANGED_LEVEL+int from SET_LEVEL_CHANGE_DETECTION
        RESPONSE_MINMAX+(int, int) from SET_RESPONSE_MINMAX_DETECTION
        VALUE+float from GET_FX, GET_FY, GET_FZ, GET_TX, GET_TY, GET_TZ,
    """
    #TODO DOCU REMOTECONTROL

    COMMAND_STR = "$cmd"

    FEEDBACK, \
    START, \
    PAUSE, \
    QUIT, \
    SET_THRESHOLDS,  \
    GET_THRESHOLD_LEVEL, \
    SET_LEVEL_CHANGE_DETECTION, \
    CHANGED_LEVEL,\
    VALUE, FILENAME, \
    GET_FX, GET_FY, GET_FZ, GET_TX, GET_TY, GET_TZ, \
    PING,\
    SET_RESPONSE_MINMAX_DETECTION, \
    RESPONSE_MINMAX,\
    GET_VERSION \
    = map(lambda x: "$cmd{0:02d}".format(x), range(20))

    FEEDBACK_PAUSED = FEEDBACK + "paused"
    FEEDBACK_STARTED = FEEDBACK + "started"


class Thresholds(object):

    def __init__(self, thresholds):
        """Thresholds for a particular sensor"""
        self._thresholds = list(thresholds)
        self._thresholds.sort()
        self._prev_level = None
        self._minmax = None

    @property
    def is_detecting(self):
        return self._minmax is not None or self._prev_level is not None

    @property
    def is_level_change_detecting(self):
        return self._prev_level is not None

    @property
    def is_response_minmax_detecting(self):
        return self._minmax is not None


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
        for cnt, x in enumerate(self._thresholds):
            if value < x:
                level = cnt
                break
        if level is None:
            level = cnt + 1
        return level

    def set_level_change_detection(self, value):
        """sets level change detection
        returns: current level
        """
        self._prev_level  = self.get_level(value)
        self._minmax = None
        return self._prev_level

    def get_level_change(self, value):
        """return tuple with level_change (boolean) and current level (int)
        if level change detection is switch on

        Note: after detected level change detection is switched off!
        """

        if self._prev_level is None:
            return None, None

        current = self.get_level(value)
        changed = (current != self._prev_level)
        if changed:
            self._prev_level = None
        return changed, current

    def __str__(self):
        return str(self._thresholds)

    def set_response_minmax_detection(self, value, duration):
        """Start response detection
        Parameters detects minimum and maximum of the response
            after first level change (length =number_of_samples)

        value: start level
        polled samples need to feed via get_response_minmax()

        returns: current level
        """

        lv = self.get_level(value)
        self._minmax = MinMaxDetector(start_value=lv,
                                     duration=duration)
        self._prev_level = None
        return lv


    def get_response_minmax(self, value):
        """checks for response minimum and maximum if set_response_minmax_detection is switch on
        With this function you add a sample and check if the response can be classified. If so,
        it returns a tuple with the minimum and maximum response level during the response period
        otherwise
            returns None

        tuple with level_change (boolean) and current level (int)

        Note: after response minmax has been determined once response_minmax_detection is switched off!
        """

        if self._minmax is None:
            return None

        rtn = self._minmax.process(self.get_level(value))
        if rtn is not None:
            # minmax just detected
            self._minmax = None # switch off
        return rtn