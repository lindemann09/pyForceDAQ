__author__ = 'Oliver Lindemann'

import ctypes as ct
from .misc import MinMaxDetector as _MinMaxDetector

# tag in data output
TAG_COMMENTS = "#"
TAG_SOFTTRIGGER = TAG_COMMENTS + "T"
TAG_UDPDATA = TAG_COMMENTS + "UDP"

CTYPE_FORCES = ct.c_float * 600
CTYPE_TRIGGER = ct.c_float * 2

class PollingPriority(object):

    NORMAL = 'normal'
    HIGH = 'high'
    REALTIME = 'real_time'

    @staticmethod
    def get_priority(priority_str):
        """returns normal or the higher priority if detected """
        if isinstance(priority_str, str):
            if priority_str.find("real") >= 0 and \
                    priority_str.find("time") >= 0:
                return PollingPriority.REALTIME
            elif priority_str.startswith("high"):
                return PollingPriority.HIGH

        return PollingPriority.NORMAL


class CTypesForceData(ct.Structure):
    _fields_ = [("device_id", ct.c_int),
            ("time", ct.c_int),
            ("forces", CTYPE_FORCES),
            ("trigger", CTYPE_TRIGGER)]


class ForceData(object):
    """The Force data structure with the following properties
        * device_id
        * time (time stamp)
        * aquisition delay (time it took to receive the new data)
        * Fx,  Fy, & Fz
        * Tx, Ty, & Tz
        * trigger1 & trigger2

    """

    forces_names = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

    def __init__(self, time=0, acquisition_delay = -1,
                 forces= [0] * 6, trigger=(0, 0),
                 device_id=0, trigger_threshold=0.9, reverse=()):
        """Create a ForceData object
        Parameters
        ----------
        device_id: int, optional
            the id of the sensor device
        time: int, optional
            the timestamp
        acquisition_delay: int, optional
            time
        forces: array of six floats
            array of the force data defined as [Fx, Fy, Fz, Tx, Ty, Tz]
        trigger: array of two floats
            two trigger values: [trigger1, trigger2]

        trigger_threshold: float (default = 0.4)
            if abs(trigger1/2) < trigger_threshold the threshold it will considered as noise
            and set to zero

        """

        self.time = time
        self.acquisition_delay = acquisition_delay
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
        if isinstance(string, str):
            self.byte_string = string.encode()
        else:
            self.byte_string = string

    @property
    def unicode(self):
        return self.byte_string.decode('utf-8', 'replace')

    @property
    def is_remote_control_command(self):
        return self.startswith(GUIRemoteControlCommands.COMMAND_STR)

    def startswith(self, byte_string):
        return self.byte_string[:len(byte_string)] == byte_string


def bytes_startswith(a, b):
    return a[:len(b)] == b


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

    #DOC REMOTECONTROL

    COMMAND_STR = b"$"
    # BASIC
    START = COMMAND_STR + b"SRT"
    PAUSE = COMMAND_STR + b"PSE"
    PING = COMMAND_STR + b"PNG"
    QUIT  = COMMAND_STR + b"QUT"
    #getter
    GET_FX1 = COMMAND_STR + b"gFX1"
    GET_FX2 = COMMAND_STR + b"gFX2"
    GET_FY1 = COMMAND_STR + b"gFY1"
    GET_FY2 = COMMAND_STR + b"gFY2"
    GET_FZ1 = COMMAND_STR + b"gFZ1"
    GET_FZ2 = COMMAND_STR + b"gFZ2"
    GET_TX1 = COMMAND_STR + b"gTX1"
    GET_TX2 = COMMAND_STR + b"gTX2"
    GET_TY1 = COMMAND_STR + b"gTY1"
    GET_TY2 = COMMAND_STR + b"gTY2"
    GET_TZ1 = COMMAND_STR + b"gTZ1"
    GET_TZ2 = COMMAND_STR + b"gTZ2"
    GET_THRESHOLD_LEVEL =COMMAND_STR + b"gTL"
    GET_THRESHOLD_LEVEL2 = COMMAND_STR + b"gTL2"
    GET_VERSION = COMMAND_STR + b"gVR"
    # setter
    FILENAME = COMMAND_STR + b"sFN"
    SET_THRESHOLDS = COMMAND_STR + b"sTH"
    SET_LEVEL_CHANGE_DETECTION = COMMAND_STR + b"sCD1"
    SET_LEVEL_CHANGE_DETECTION2 = COMMAND_STR + b"sCD2"
    SET_RESPONSE_MINMAX_DETECTION = COMMAND_STR + b"sMD1"
    SET_RESPONSE_MINMAX_DETECTION2 = COMMAND_STR + b"sMD2"
    #feedback
    FEEDBACK = COMMAND_STR + b"xFB"
    VALUE = COMMAND_STR + b"xVL"
    RESPONSE_MINMAX = COMMAND_STR + b"xRM1"
    RESPONSE_MINMAX2 = COMMAND_STR + b"xRM2"
    CHANGED_LEVEL = COMMAND_STR + b"xCL1"
    CHANGED_LEVEL2 = COMMAND_STR + b"xCL2"

    FEEDBACK_PAUSED = FEEDBACK + b"paused"
    FEEDBACK_STARTED = FEEDBACK + b"started"

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
        return len(list(filter(nn, self._prev_level)))>0 or len(list(filter(nn, self._minmax)))>0

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
        self._minmax[channel] = _MinMaxDetector(start_value=lv,
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