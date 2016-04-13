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
        * trigger1 & trigger2

    """

    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

    def __init__(self, time=0, forces=[0] * 6, trigger=(0, 0),
                 device_id=0, trigger_threshold=0.9, reverse=()):
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

        trigger_threshold: float (default = 0.4)
            if abs(trigger1/2) < trigger_threshold the threshold it will considered as noise
            and set to zero

        """

        self.time = time
        self.device_id = device_id
        self.forces = forces
        self.trigger = list(trigger)
        if abs(self.trigger[0]) < trigger_threshold:
            self.trigger[0] = 0
        if abs(self.trigger[1]) < trigger_threshold:
            self.trigger[1] = 0
        for r in reverse:
            forces[r] = -1*forces[r]

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
        return self.forces[5]

    @Tz.setter
    def Tz(self, value):
        self.forces[5] = value

    @property
    def ctypes_struct(self):
        return CTypesForceData(self.device_id, self.time,
              CTYPE_FORCES(*self.forces), CTYPE_TRIGGER(*self.trigger))

    @ctypes_struct.setter
    def ctypes_struct(self, struct):
        self.device_id = struct.device_id
        self.time = struct.time
        self.force = struct.forces
        self.trigger = struct.trigger



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

    @property
    def is_remote_control_command(self):
        return self.string.startswith(GUIRemoteControlCommands.COMMAND_STR)



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

    see also UDPConnection constants!
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
    GET_VERSION, \
    GET_FX2, GET_FY2, GET_FZ2, GET_TX2, GET_TY2, GET_TZ2,\
    GET_THRESHOLD_LEVEL2, \
    SET_LEVEL_CHANGE_DETECTION2, \
    CHANGED_LEVEL2, \
    SET_RESPONSE_MINMAX_DETECTION2, \
    RESPONSE_MINMAX2\
    = map(lambda x: "$cmd{0:02d}:".format(x), range(31))

    FEEDBACK_PAUSED = FEEDBACK + "paused"
    FEEDBACK_STARTED = FEEDBACK + "started"

class Thresholds(object):

    def __init__(self, thresholds, n_channels=1):
        """Thresholds for a one or multiple channels of data"""
        self._thresholds = list(thresholds)
        self._thresholds.sort()
        self.set_number_of_channels(n_channels=n_channels)

    def is_detecting(self, channels=0):
        return self._minmax[channels] is not None or self._prev_level[channels] is not None

    def is_level_change_detecting(self, channels=0):
        return self._prev_level[channels] is not None

    def is_response_minmax_detecting(self, channels=0):
        return self._minmax[channels] is not None

    def is_detecting_anything(self):
        """is detecting something in at least one channel"""
        nn = lambda x:x is not None
        return len(filter(nn, self._prev_level))>0 or len(filter(nn, self._minmax))>0

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
        self._prev_level[channel]  = self.get_level(value)
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
        changed = (current != self._prev_level[channel])
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
        self._minmax[channel] = MinMaxDetector(start_value=lv,
                                     duration=duration)
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
            self._minmax[channel] = None # switch off
        return rtn