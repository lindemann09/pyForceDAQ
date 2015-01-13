"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = 'Oliver Lindemann'

import ctypes as ct
from multiprocessing import Process, Event, sharedctypes
import atexit
from time import sleep

import numpy as np

from pyATIDAQ import ATI_CDLL
from nidaq import DAQConfiguration, DAQReadAnalog
from clock import Clock


class ForceData(object):
    """The Force data structure with the following properties
        * device_id
        * Fx,  Fy, & Fz
        * Tx, Ty, & Tz
        * trigger1 & trigger2
        * time
        * counter

    """

    variable_names = "device_id, time, counter, Fx, Fy, Fz, Tx, Ty, Tz, " + \
                     "trigger1, trigger2"

    def __init__(self, time = None, counter=0, forces = [0]*6, trigger=[0, 0],
                 device_id=0):
        """Create a ForceData object
        Parameters
        ----------
        device_id: int, optional
            the id of the sensor device
        time: int, optional
            the timestamp
        counter: int
            sample counter; useful, for instance, if multiple samples are
            received within one millisecond
        forces: array of six floats
            array of the force data defined as [Fx, Fy, Fz, Tx, Ty, Tz]
        trigger: array of two floats
            two trigger values: [trigger1, trigger2]

        """

        self.time = time
        self.device_id = device_id
        self.counter = counter
        self.Fx, self.Fy, self.Fz, self.Tx, self.Ty, self.Tz = forces
        self.trigger = trigger

    def __str__(self):
        """converts data to string. """
        txt = "%d,%d,%d, %.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (self.device_id,
                self.time, self.counter,
                self.Fx, self.Fy, self.Fz, self.Tx, self.Ty, self.Tz)
        txt += ",%.4f,%.4f" % (self.trigger[0], self.trigger[1])
        return txt

    @property
    def force_np_array(self):
        """numpy array of all force data"""
        return np.array([self.Fx, self.Fy, self.Fz, self.Tx, self.Ty, self.Tz])

class SensorSettings(DAQConfiguration):

    def __init__(self, calibration_file, sync_clock, device_id=1, channels="ai0:7",
                        rate=1000, minVal = -10,  maxVal = 10):

        DAQConfiguration.__init__(self, device_id=device_id, channels=channels,
                             rate=rate, minVal = minVal,  maxVal = maxVal)
        self.sync_clock = sync_clock
        self.calibration_file = calibration_file

class Sensor(DAQReadAnalog):

    SENSOR_CHANNELS = range(0, 5+1)  # channel 0:5 for FT sensor, channel 6 for trigger
    TRIGGER_CHANNELS = range(5, 6+1) # channel 7 for trigger synchronization validation

    def __init__(self, settings):
        """ TODO"""

        DAQReadAnalog.__init__(self, configuration=settings,
                    read_array_size_in_samples = \
                    len(Sensor.SENSOR_CHANNELS) + len(Sensor.TRIGGER_CHANNELS))

        # ATI voltage to forrce converter
        self._atidaq = ATI_CDLL()
        # get calibration
        index = ct.c_short(1)
        self._atidaq.createCalibration(settings.calibration_file, index)
        self._atidaq.setForceUnits("N")
        self._atidaq.setTorqueUnits("N-m")

        self._clock = Clock(settings.sync_clock)
        self._last_sample_time_counter = (0, 0) # time & cunter

    def determine_bias(self, n_samples=100):
        """determines the bias

        """

        task_was_running = self._task_is_started
        self.start_data_acquisition()
        data = None
        for x in range(n_samples):
            read_buffer, _read_samples = self.read_analog()
            sample = read_buffer[Sensor.SENSOR_CHANNELS]
            if data is None:
                data = sample
            else:
                data = np.vstack((data, sample))

        if not task_was_running:
            self.stop_data_acquisition()

        self._atidaq.bias(np.mean(data, axis=0))

    def poll_force_data(self):
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the ATIDAO libraray.

        Returns
        -------
        data: ForceData
            the converted force data as ForceData object

        """

        read_buffer, _read_samples = self.read_analog()
        time = self._clock.time

        data = ForceData(time = time, device_id = self.device_id,
                forces = self._atidaq.convertToFT(read_buffer[Sensor.SENSOR_CHANNELS]),
                trigger = read_buffer[Sensor.TRIGGER_CHANNELS].tolist())

        # set counter if multiple sample in same millisecond
        if data.time > self._last_sample_time_counter[0]:
            self._last_sample_time_counter = (data.time, 0)
        else:
            self._last_sample_time_counter = (data.time,
                                        self._last_sample_time_counter[1]+1)
        data.counter = self._last_sample_time_counter[1]

        return data

class SensorProcess(Process):

    def __init__(self, settings, data_queue=None, write_queue_after_pause=True):
        """ForceSensorProcess

        if no data_queue will be set no data will be buffered
        write_queue_after_pause: does not write shared data queue continuously and
            writes it the buffer data to queue only after pause (or stop)

        """

        # todo: explain usage

        #type checks
        if not isinstance(settings, SensorSettings):
            raise RuntimeError("settings has to be force_sensor.Settings object")

        super(SensorProcess, self).__init__()
        self.sensor_settings = settings
        self.data_queue = data_queue
        self._write_queue_after_pause = write_queue_after_pause
        self._event_polling = Event()
        self.event_bias_is_available = Event()
        self.daemon = True

        self._last_Fx = sharedctypes.RawValue(ct.c_float)
        self._last_Fy = sharedctypes.RawValue(ct.c_float)
        self._last_Fz = sharedctypes.RawValue(ct.c_float)
        self._last_Tx = sharedctypes.RawValue(ct.c_float)
        self._last_Ty = sharedctypes.RawValue(ct.c_float)
        self._last_Tz = sharedctypes.RawValue(ct.c_float)
        self._buffer_size = sharedctypes.RawValue(ct.c_uint64)
        self._sample_cnt = sharedctypes.Value(ct.c_uint64)

        self._event_stop_request = Event()
        self._determine_bias_flag = Event()

        self._bias_n_samples = 200
        atexit.register(self.stop)

    @property
    def Fx(self):
        return self._last_Fx.value

    @property
    def Fy(self):
        return self._last_Fy.value

    @property
    def Fz(self):
        return self._last_Fz.value

    @property
    def Tx(self):
        return self._last_Tx.value

    @property
    def Ty(self):
        return self._last_Ty.value

    @property
    def Tz(self):
        return self._last_Tz.value

    @property
    def sample_cnt(self):
        return self._sample_cnt.value

    @property
    def buffer_size(self):
        return self._buffer_size.value

    def determine_bias(self, n_samples=100): # FIXME chnaging no samples. Does that work?
        """recording is paused after bias determination

        This process might take a while. Please use "wait_bias_available" to
        ensure that the process is finished and the sensor is again read for
        recording.
        """

        self._bias_n_samples = n_samples
        self.event_bias_is_available.clear()
        self._determine_bias_flag.set()

    def start_polling(self):
        self._event_polling.set()

    def pause_polling_and_write_queue(self):
        """pause polling and write data queue"""
        if self._event_polling.is_set():
            self._event_polling.clear()
            while self.buffer_size > 0: # wait until buffer is empty and queue is written
                sleep(0.001)

    def stop(self):
        if self.is_alive():
            self.join(2)
        if self.is_alive():
            self.terminate()

    def join(self, timeout=None):
            self.pause_polling_and_write_queue()
            self._event_stop_request.set()
            super(SensorProcess, self).join(timeout)



    def run(self):
        buffer = []
        self._buffer_size.value = 0
        sensor = Sensor(self.sensor_settings)
        self.pause_polling_and_write_queue()
        is_polling = False
        while not self._event_stop_request.is_set():
            if self._event_polling.is_set():
                if not is_polling:
                    # start NI device and acquire one first dummy sample to
                    # ensure good timing
                    sensor.start_data_acquisition()
                    sensor.poll_force_data()
                    is_polling = True
                data = sensor.poll_force_data()
                if self.data_queue is not None:
                    if self._write_queue_after_pause:
                        buffer.append(data)
                        self._buffer_size.value = len(buffer)
                    else:
                        self.data_queue.put(data)
                self._last_Fx.value = data.Fx
                self._last_Fy.value = data.Fy
                self._last_Fz.value = data.Fz
                self._last_Tx.value = data.Tx
                self._last_Ty.value = data.Ty
                self._last_Tz.value = data.Tz
                self._sample_cnt.value += 1
            else:
                # not polling
                if is_polling:
                    sensor.stop_data_acquisition()
                    is_polling = False

                while len(buffer) > 0:
                    self.data_queue.put(buffer.pop(0))
                    self._buffer_size.value = len(buffer)

            if self._determine_bias_flag.is_set():
                sensor.stop_data_acquisition()
                is_polling = False
                self._event_polling.clear()
                sensor.determine_bias(n_samples=self._bias_n_samples)
                self._determine_bias_flag.clear()
                self.event_bias_is_available.set()

        sensor.stop_data_acquisition()