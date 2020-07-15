import ctypes as ct

NUM_SAMPS_PER_CHAN = ct.c_int32(1)
TIMEOUT = ct.c_longdouble(1.0)  # one second
NI_DAQ_BUFFER_SIZE = 1000
#TODO setting files?

class DAQConfiguration(object):
    """Settings required for NI-DAQ"""
    def __init__(self, device_name, channels="ai0:7",
                 rate=1000, minVal = -10,  maxVal = 10):
        self.device_name = device_name
        self.channels = channels
        self.rate = ct.c_double(rate)
        self.minVal = ct.c_double(minVal)
        self.maxVal = ct.c_double(maxVal)

    @property
    def physicalChannel(self):
        return "{0}/{1}".format(self.device_name, self.channels)
