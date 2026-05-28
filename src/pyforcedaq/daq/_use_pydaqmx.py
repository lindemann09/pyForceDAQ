"""Module to read data analog data from NI-DAQ device

A simple high-level wrapper for NI-DAQmx functions

Requires: PyDAQmx, Numpy

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = 'Oliver Lindemann'

import ctypes as ct
from typing import Tuple

import numpy as np
import PyDAQmx

from .._lib.settings import DAQConfiguration


class DAQReadAnalog(PyDAQmx.Task):

    NUM_SAMPS_PER_CHAN = ct.c_int32(1)
    TIMEOUT = ct.c_longdouble(1.0)  # one second
    NI_DAQ_BUFFER_SIZE = 1000
    DAQ_TYPE = "PyDAQmx"

    def __init__(self, configuration: DAQConfiguration, read_array_size_in_samples: int ):
        """ DOC
        read_array_size_in_samples for ReadAnalogF64 call

        """

        # print('init')
        PyDAQmx.Task.__init__(self)
        # CreateAIVoltageChan
        self.CreateAIVoltageChan(configuration.physicalChannel,
                                 # physicalChannel
                                 "",  # nameToAssignToChannel,
                                 PyDAQmx.DAQmx_Val_Diff,  # terminalConfig
                                 ct.c_double(configuration.minVal),
                                 ct.c_double(configuration.maxVal),
                                 # min max Val
                                 PyDAQmx.DAQmx_Val_Volts,  # units
                                 None  # customScaleName
                                 )

        # CfgSampClkTiming
        self.CfgSampClkTiming("",  # source
                              ct.c_double(float(configuration.rate)),  # rate
                              PyDAQmx.DAQmx_Val_Rising,  # activeEdge
                              PyDAQmx.DAQmx_Val_ContSamps,  # sampleMode
                              ct.c_uint64(DAQReadAnalog.NI_DAQ_BUFFER_SIZE)
                              # sampsPerChanToAcquire, i.e. buffer size
                              )

        self._task_is_started = False
        self.read_array_size_in_samples = read_array_size_in_samples

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

    def read_analog(self) -> Tuple[np.ndarray, int]:
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

        # fill in data
        read_samples = ct.c_int32()
        read_buffer = np.zeros((self.read_array_size_in_samples,),
                               dtype=np.float64)

        error = self.ReadAnalogF64(self.NUM_SAMPS_PER_CHAN,
                                   self.TIMEOUT,
                                   PyDAQmx.DAQmx_Val_GroupByScanNumber,
                                   # fillMode
                                   read_buffer,
                                   ct.c_uint32(self.read_array_size_in_samples),
                                   ct.byref(read_samples),
                                   None)
        print(read_buffer)
        return read_buffer, read_samples.value
