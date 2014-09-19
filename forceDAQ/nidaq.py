"""Module to read data analog data from NI-DAQ device

A simple high-level wrapper for NI-DAQmx functions

Requires: PyDAQmx, Numpy

"""

__author__ = 'Oliver Lindemann'
__version__ = "0.1"

import ctypes as ct
import numpy as np
import PyDAQmx

class DAQConfiguration(object):
    """Settings required for NI-DAQ"""
    def __init__(self, device_id=1, channels="ai0:7", rate=1000, minVal = -10,  maxVal = 10):
        self.device_id = device_id
        self.channels = channels
        self.rate = ct.c_double(rate)
        self.minVal = ct.c_double(minVal)
        self.maxVal = ct.c_double(maxVal)

    @property
    def physicalChannel(self):
        return "Dev{0}/{1}".format(self.device_id, self.channels)

class DAQReadAnalog(PyDAQmx.Task):

    NUM_SAMPS_PER_CHAN = ct.c_int32(1)
    TIMEOUT = ct.c_longdouble(1.0) # one second
    NI_DAQ_BUFFER_SIZE = 1000

    def __init__(self, configuration, read_array_size_in_samples):
        """ TODO
        read_array_size_in_samples for ReadAnalogF64 call

        """

        PyDAQmx.Task.__init__(self)

        # CreateAIVoltageChan
        self.CreateAIVoltageChan(configuration.physicalChannel, # physicalChannel
                            "",                         # nameToAssignToChannel,
                            PyDAQmx.DAQmx_Val_Diff,     # terminalConfig
                            configuration.minVal, configuration.maxVal,  # min max Val
                            PyDAQmx.DAQmx_Val_Volts,    # units
                            None                        # customScaleName
                            )

        #CfgSampClkTiming
        self.CfgSampClkTiming("",                 # source
                            configuration.rate,          # rate
                            PyDAQmx.DAQmx_Val_Rising,   # activeEdge
                            PyDAQmx.DAQmx_Val_ContSamps,# sampleMode
                            ct.c_uint64(DAQReadAnalog.NI_DAQ_BUFFER_SIZE) # sampsPerChanToAcquire, i.e. buffer size
                            )

        self.device_id = configuration.device_id
        self._task_is_started = False
        self.read_array_size_in_samples = ct.c_uint32(read_array_size_in_samples)

    @property
    def is_acquiring_data(self):
        return self._task_is_started

    def start_data_acquisition(self):
        """Start data acquisition of the NI device
        call always before polling

        """

        if not self._task_is_started:
            self.StartTask()
            self._task_is_started = True

    def stop_data_acquisition(self):
        """ Stop data acquisition of the NI device
        """

        if self._task_is_started:
            self.StopTask()
            self._task_is_started = False

    def read_analog(self):
        """Polling data

        Reading data from NI device

        Parameter
        ---------
        array_size_in_samps : int
            the array size in number of samples

        Returns
        -------
        read_buffer : numpy array
            the read data
        read_samples : int
            the number of read samples

        """

        #fill in data
        read_samples = ct.c_int32()
        read_buffer = np.zeros((self.read_array_size_in_samples.values,), dtype=np.float64)

        error = self.ReadAnalogF64(DAQReadAnalog.NUM_SAMPS_PER_CHAN,
                                DAQReadAnalog.TIMEOUT,
                                PyDAQmx.DAQmx_Val_GroupByScanNumber, # fillMode
                                read_buffer,
                                self.read_array_size_in_samples,
                                ct.byref(read_samples), None) # TODO: process error?

        return read_buffer, read_samples.value
