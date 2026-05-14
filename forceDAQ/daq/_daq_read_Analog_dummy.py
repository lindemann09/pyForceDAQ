__author__ = 'Oliver Lindemann'

import logging

import numpy as np

from .._lib.timer import Clock


class DAQReadAnalog(object):
    NUM_SAMPS_PER_CHAN =  1
    TIMEOUT = 1.0
    NI_DAQ_BUFFER_SIZE = 1000
    DAQ_TYPE = "dummy"

    def __init__(self, configuration=None,
                 read_array_size_in_samples=None):
        self.read_array_size_in_samples = read_array_size_in_samples
        self._task_is_started = False
        self._last_time = 0
        self._sample_cnt = 0
        self._simulation_timer = Clock()
        txt = "Using dummy sensor: Maybe PyDAQmx or nidaqmx is not  installed"
        logging.warning(txt)
        print(txt)


    @property
    def is_acquiring_data(self):
        return self._task_is_started

    def start_data_acquisition(self):
        """Start data acquisition of the NI device
        call always before polling

        """

        if not self._task_is_started:
            self._task_is_started = True
            self._simulation_timer = Clock() #reset
            self._sample_cnt = 0

    def stop_data_acquisition(self):
        """ Stop data acquisition of the NI device
        """

        if self._task_is_started:
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

        n_new_samples = self._simulation_timer.time - self._sample_cnt
        while n_new_samples <= 0:
            n_new_samples = self._simulation_timer.time - self._sample_cnt

        self._sample_cnt += 1
        x = self._sample_cnt / 2000
        y = 10 + np.array((np.sin(x/2), np.cos(x/5), np.sin(x)))*10
        return np.append(y, np.array((0, 0 , 0, 0, 0))), 1
