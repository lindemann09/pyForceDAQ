"""class to record force sensor data"""

__author__ = "Oliver Lindemann"

import ctypes as ct
import numpy as np
from multiprocessing import Process, Event
import atexit

import PyDAQmx
from pyATIDAQ import ATI_CDLL
from clock import Clock


# Constants
SENSOR_CHANNELS = range(0, 5+1)  # channel 0:5 for FT sensor, channel 6 for trigger
TRIGGER_CHANNELS = range(5, 6+1) # channel 7 for trigger synchronization validation
ARRAY_SIZE_IN_SAMPS = ct.c_uint32(len(SENSOR_CHANNELS) + len(TRIGGER_CHANNELS))

# ReadAnalogF64 settings
NUM_SAMPS_PER_CHAN = ct.c_int32(1)
TIMEOUT = ct.c_longdouble(1.0) # one second
NI_DAQ_BUFFER_SIZE = 1000

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
        self.trigger1 = trigger[0]
        self.trigger2 = trigger[1]

    def __str__(self):
        """converts data to string. """
        txt = "%d,%d,%d, %.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (self.device_id,
                self.time, self.counter,
                self.Fx, self.Fy, self.Fz, self.Tx, self.Ty, self.Tz)
        txt += ",%.4f,%.4f" % (self.trigger1, self.trigger2)
        return txt

    @property
    def force_np_array(self):
        """numpy array of all force data"""
        return np.array([self.Fx, self.Fy, self.Fz, self.Tx, self.Ty, self.Tz])

    @property
    def trigger_np_array(self):
        """numpy array of all trigger data """
        return np.array([self.trigger1, self.trigger2])


class DAQSettings(object):
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

class Settings(DAQSettings):

    def __init__(self, calibration_file, sync_clock, device_id=1, channels="ai0:7",
                        rate=1000, minVal = -10,  maxVal = 10):

        DAQSettings.__init__(self, device_id=device_id, channels=channels,
                             rate=rate, minVal = minVal,  maxVal = maxVal)
        self.sync_clock = sync_clock
        self.calibration_file = calibration_file

class Sensor(PyDAQmx.Task):

    def __init__(self, settings):
        """ TODO"""

        PyDAQmx.Task.__init__(self)

        # ATI voltage to forrce converter
        self._atidaq = ATI_CDLL()
        # get calibration
        index = ct.c_short(1)
        self._atidaq.createCalibration(settings.calibration_file, index)
        self._atidaq.setForceUnits("N")
        self._atidaq.setTorqueUnits("N-m")

        # CreateAIVoltageChan
        self.CreateAIVoltageChan(settings.physicalChannel, # physicalChannel
                            "",                         # nameToAssignToChannel,
                            PyDAQmx.DAQmx_Val_Diff,     # terminalConfig
                            settings.minVal, settings.maxVal,  # min max Val
                            PyDAQmx.DAQmx_Val_Volts,    # units
                            None                        # customScaleName
                            )

        #CfgSampClkTiming
        self.CfgSampClkTiming("",                 # source
                            settings.rate,          # rate
                            PyDAQmx.DAQmx_Val_Rising,   # activeEdge
                            PyDAQmx.DAQmx_Val_ContSamps,# sampleMode
                            ct.c_uint64(NI_DAQ_BUFFER_SIZE) # sampsPerChanToAcquire, i.e. buffer size
                            )

        self.device_id = settings.device_id
        self._task_is_started = False
        self._clock = Clock(settings.sync_clock)
        self._last_sample_time_counter = (0, 0) # time & cunter

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

        # fill in data
        read_samples = ct.c_int32()
        read_buffer = np.zeros((ARRAY_SIZE_IN_SAMPS.value,), dtype=np.float64)

        error = self.ReadAnalogF64(NUM_SAMPS_PER_CHAN, TIMEOUT,
                                PyDAQmx.DAQmx_Val_GroupByScanNumber, # fillMode
                                read_buffer,
                                ARRAY_SIZE_IN_SAMPS,
                                ct.byref(read_samples), None) # TODO: process error

        data = ForceData(time = self._clock.time,
                device_id = self.device_id,
                forces = self._atidaq.convertToFT(read_buffer[SENSOR_CHANNELS]),
                trigger = read_buffer[TRIGGER_CHANNELS].tolist()) # todo test: does it work without np.copy

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
