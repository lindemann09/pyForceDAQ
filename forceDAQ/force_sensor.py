"""class to record force sensor data"""
import ctypes as ct
import numpy as np
from multiprocessing import Process, Event
import atexit

import PyDAQmx
from pyATIDAQ import ATI_CDLL

from clock import Clock


# Constants
# force sensor settings
SENSOR_CHANNELS = range(0, 5+1)  # channel 0:5 for FT sensor, channel 6 for trigger
TRIGGER_CHANNELS = range(5, 6+1) # channel 7 for trigger synchronization validation

# ReadAnalogF64 settings
NUM_SAMPS_PER_CHAN = ct.c_int32(1)
TIMEOUT = ct.c_longdouble(1.0) # one second
ARRAY_SIZE_IN_SAMPS = ct.c_uint32(len(SENSOR_CHANNELS) + len(TRIGGER_CHANNELS))

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

class Settings():

    def __init__(self, calibration_file, sync_clock, device_id=1, channels="ai0:7",
                        rate=1000, minVal = -10,  maxVal = 10):
        self.sync_clock = sync_clock
        self.device_id = device_id
        self.rate = rate
        self.minVal = minVal
        self.maxVal = maxVal
        self.channels = channels
        self.calibration_file = calibration_file

class Sensor(PyDAQmx.Task):

    def __init__(self, force_sensor_settings):
        """ TODO"""

        PyDAQmx.Task.__init__(self)

        # ATI voltage to forrce converter
        self._atidaq = ATI_CDLL()
        # get calibration
        index = ct.c_short(1)
        self._atidaq.createCalibration(force_sensor_settings.calibration_file, index)
        self._atidaq.setForceUnits("N")
        self._atidaq.setTorqueUnits("N-m")

        # CreateAIVoltageChan
        physicalChannel = "Dev{0}/{1}".format(force_sensor_settings.device_id,
                                              force_sensor_settings.channels)
        self.CreateAIVoltageChan(physicalChannel, # physicalChannel
                            "",                         # nameToAssignToChannel,
                            PyDAQmx.DAQmx_Val_Diff,     # terminalConfig
                            ct.c_double(force_sensor_settings.minVal),
                            ct.c_double(force_sensor_settings.maxVal),  # min max Val
                            PyDAQmx.DAQmx_Val_Volts,    # units
                            None                        # customScaleName
                            )

        #CfgSampClkTiming
        self.CfgSampClkTiming("",                 # source
                            ct.c_double(force_sensor_settings.rate),          # rate
                            PyDAQmx.DAQmx_Val_Rising,   # activeEdge
                            PyDAQmx.DAQmx_Val_ContSamps,# sampleMode
                            ct.c_uint64(NI_DAQ_BUFFER_SIZE) # sampsPerChanToAcquire, i.e. buffer size
                            )

        # fill in data
        self.read_samples = ct.c_int32()
        self.read_buffer = np.zeros((ARRAY_SIZE_IN_SAMPS.value,), dtype=np.float64)

        self.device_id = force_sensor_settings.device_id
        self._task_is_started = False
        self._clock = Clock(force_sensor_settings.sync_clock)
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
            sample = self.poll_data(convert_to_force=False)
            if data is None:
                data = sample.force_np_array
            else:
                data = np.vstack((data, sample.force_np_array))

        if not task_was_running:
            self.stop_data_acquisition()

        self._atidaq.bias(np.mean(data, axis=0))

    def poll_data(self, convert_to_force=True, return_trigger=True):
        """polling data and timestamp data. run StartTask before polling

        TODO document data dict

        Returns ForceData
        """

        rtn = {}
        error = self.ReadAnalogF64(NUM_SAMPS_PER_CHAN, TIMEOUT,
                                PyDAQmx.DAQmx_Val_GroupByScanNumber, # fillMode
                                self.read_buffer,
                                ARRAY_SIZE_IN_SAMPS,
                                ct.byref(self.read_samples), None) # TODO: process error

        time = self._clock.time
        if convert_to_force:
            forces = self._atidaq.convertToFT(self.read_buffer[SENSOR_CHANNELS]) # TODO: Does that work with numpy arrays
        else:
            forces = self.read_buffer[SENSOR_CHANNELS]
        if return_trigger:
            trigger = np.copy(self.read_buffer[TRIGGER_CHANNELS])
        else:
            trigger = [0,0]

        # set counter if multiple sample in same millisecond
        if time > self._last_sample_time_counter[0]:
            self._last_sample_time_counter = (time, 0)
        else:
            self._last_sample_time_counter = (time,
                                        self._last_sample_time_counter[1]+1)

        return ForceData(time = time,
                         counter = self._last_sample_time_counter[1],
                         forces=forces,
                         trigger=trigger,
                         device_id=self.device_id)

class SensorProcess(Process):

    def __init__(self, force_sensor_settings, data_queue, read_trigger=True):
        """ForceSensorProcess
        """
        # todo: explain usage

        #type checks
        if not isinstance(force_sensor_settings, Settings):
            raise RuntimeError("force_sensor_settings has to be force_sensor.Settings object")

        super(SensorProcess, self).__init__()
        self.sensor_settings = force_sensor_settings
        self.data_queue = data_queue
        self.read_trigger = read_trigger

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
                    sensor.poll_data(convert_to_force=True,
                                return_trigger=self.read_trigger)
                    is_polling = True
                data = sensor.poll_data(convert_to_force=True,
                                            return_trigger=self.read_trigger)
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
