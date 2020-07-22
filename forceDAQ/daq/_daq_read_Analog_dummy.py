__author__ = 'Oliver Lindemann'

import numpy as np
from time import sleep
from .._lib.timer import Timer
from ._config import NUM_SAMPS_PER_CHAN, TIMEOUT, NI_DAQ_BUFFER_SIZE

class DAQReadAnalog(object):
    NUM_SAMPS_PER_CHAN =  NUM_SAMPS_PER_CHAN
    TIMEOUT = TIMEOUT
    NI_DAQ_BUFFER_SIZE = NI_DAQ_BUFFER_SIZE
    DAQ_TYPE = "dummy"

    def __init__(self, configuration=None,
                 read_array_size_in_samples=None):
        self.read_array_size_in_samples = read_array_size_in_samples
        self._task_is_started = False
        self._last_time = 0
        self._sample_cnt = 0
        self._runtimer = Timer()
        print("Using dummy sensor: Maybe PyDAQmx or nidaqmx is not installed")

    @property
    def is_acquiring_data(self):
        return self._task_is_started

    def start_data_acquisition(self):
        """Start data acquisition of the NI device
        call always before polling

        """

        if not self._task_is_started:
            print("dummy: started")
            self._task_is_started = True
            self._runtimer = Timer()
            self._sample_cnt = 0

    def stop_data_acquisition(self):
        """ Stop data acquisition of the NI device
        """

        if self._task_is_started:
            print("dummy: stopped")
            self._task_is_started = False

    def read_analog(self):
        """Reading data

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
        if not self._task_is_started:
            return None, None

        n_new_samples = self._runtimer.time - self._sample_cnt
        while n_new_samples <= 0:
            sleep(0.0001) # simulate slow access time
            n_new_samples = self._runtimer.time - self._sample_cnt

        self._sample_cnt += 1
        x = self._sample_cnt / 2000
        y = 10 + np.array((np.sin(x/2), np.cos(x/5), np.sin(x)))*10
        return np.append(y, np.array((0, 0 , 0, 0, 0))), 1

#FIXME why does pause not work for dummy sensors