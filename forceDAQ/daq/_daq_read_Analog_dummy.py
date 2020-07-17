__author__ = 'Oliver Lindemann'

from ._config import NUM_SAMPS_PER_CHAN, TIMEOUT, NI_DAQ_BUFFER_SIZE

class DAQReadAnalog(object):
    NUM_SAMPS_PER_CHAN =  NUM_SAMPS_PER_CHAN
    TIMEOUT = TIMEOUT
    NI_DAQ_BUFFER_SIZE = NI_DAQ_BUFFER_SIZE

    def __init__(self, configuration=None,
                 read_array_size_in_samples=None):
        self.configuration = configuration
        self.read_array_size_in_samples = read_array_size_in_samples
        #TODO simulate NI-DAQ

        raise RuntimeError("PyDAQmx or nidaqmx is not installed")