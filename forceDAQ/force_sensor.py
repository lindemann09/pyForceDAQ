"""class to record force sensor data"""

__author__ = 'Oliver Lindemann'

import ctypes as ct
import numpy as np
from multiprocessing import Process, Event
import atexit

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

class Settings(DAQConfiguration):

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
            sample = self.poll_data()
            if data is None:
                data = sample.force_np_array
            else:
                data = np.vstack((data, sample.force_np_array))

        if not task_was_running:
            self.stop_data_acquisition()

        self._atidaq.bias(np.mean(data, axis=0))

    def poll_data(self):
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the ATIDAO libraray.

        Returns
        -------
        data: ForceData
            the converted force data as ForceData object

        """

        read_buffer, read_samples = self.read_analog()

        data = ForceData(time = self._clock.time,
                device_id = self.device_id,
                forces = self._atidaq.convertToFT(read_buffer[Sensor.SENSOR_CHANNELS]),
                trigger = read_buffer[Sensor.TRIGGER_CHANNELS].tolist()) # todo test: does it work without np.copy

        # set counter if multiple sample in same millisecond
        if data.time > self._last_sample_time_counter[0]:
            self._last_sample_time_counter = (data.time, 0)
        else:
            self._last_sample_time_counter = (data.time,
                                        self._last_sample_time_counter[1]+1)
        data.counter = self._last_sample_time_counter[1]

        return data

class SensorProcess(Process):

    def __init__(self, settings, data_queue):
        """ForceSensorProcess
        """
        # todo: explain usage

        #type checks
        if not isinstance(settings, Settings):
            raise RuntimeError("settings has to be force_sensor.Settings object")

        super(SensorProcess, self).__init__()
        self.sensor_settings = settings
        self.data_queue = data_queue

        self.event_polling = Event()
        self.event_bias_is_available = Event()

        self._event_stop_request = Event()
        self._determine_bias_flag = Event()
        self._bias_n_samples = 200
        atexit.register(self.stop)

    def determine_bias(self, n_samples=100):
        """recording is paused after bias determination

        This process might take a while. Please use "wait_bias_available" to
        ensure that the process is finished and the sensor is again read for
        recording.
        """

        self._bias_n_samples = n_samples
        self.event_bias_is_available.clear()
        self._determine_bias_flag.set()

    def stop(self):
        self._event_stop_request.set()

    def run(self):
        sensor = Sensor(self.sensor_settings)
        self.event_polling.clear()
        is_polling = False
        while not self._event_stop_request.is_set():
            if self.event_polling.is_set():
                if not is_polling:
                    # start NI device and acquire one first dummy sample to
                    # ensure good timing
                    sensor.start_data_acquisition()
                    sensor.poll_data()
                    is_polling = True
                data = sensor.poll_data()
                self.data_queue.put_nowait(data)
            else:
                if is_polling:
                    sensor.stop_data_acquisition()
                    is_polling = False
                self.event_polling.wait(timeout=0.2)

            if self._determine_bias_flag.is_set():
                sensor.stop_data_acquisition()
                is_polling = False
                sensor.determine_bias(n_samples=self._bias_n_samples)
                self._determine_bias_flag.clear()
                self.event_bias_is_available.set()

        sensor.stop_data_acquisition()
