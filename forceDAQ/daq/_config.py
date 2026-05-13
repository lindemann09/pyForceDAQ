class DAQConfiguration(object):
    """Settings required for NI-DAQ"""
    def __init__(self, device_name: str, channels: str = "ai0:7",
                 rate: float = 1000, minVal: float = -10,  maxVal: float = 10):
        self.device_name = device_name
        self.channels = channels
        self.rate = rate
        self.minVal = minVal
        self.maxVal = maxVal

    @property
    def physicalChannel(self):
        return "{0}/{1}".format(self.device_name, self.channels)
