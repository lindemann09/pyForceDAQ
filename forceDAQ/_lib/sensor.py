"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = 'Oliver Lindemann'

import atexit
import ctypes as ct
from copy import copy
from multiprocessing import Process, Event, sharedctypes, Pipe
from time import sleep

import numpy as np

from ..daq import ATI_CDLL, DAQConfiguration, find_calibration_file
from .types import ForceData, DAQEvents
from .timer import Timer

from ..daq import DAQReadAnalog

class SensorSettings(DAQConfiguration):
    def __init__(self,
                 device_id,
                 sensor_name,
                 calibration_folder,
                 sync_timer,
                 channels="ai0:7",
                 device_name_prefix = "Dev",
                 rate=1000,
                 minVal=-10,
                 maxVal=10,
                 reverse_parameter_names=()):

        """
        :parameter:
            reverse_scaling: string or list of string
                list of parameter names for which the scaling needs to be reversed (e.g. to fix problems with calibration),
                Sensors take this into account and correct data online
        """

        DAQConfiguration.__init__(self,
                                  device_name = "{0}{1}".format(device_name_prefix, device_id),
                                  channels=channels,
                                  rate=rate, minVal=minVal, maxVal=maxVal)
        self.sync_timer = sync_timer
        self.device_id = device_id
        self.sensor_name = sensor_name
        self.calibration_file = find_calibration_file(
                                        calibration_folder=calibration_folder,
                                        sensor_name=sensor_name,
                                        calibration_suffix=".cal")

        self.reverse_parameters = []
        if not isinstance(reverse_parameter_names, (tuple, list)):
            reverse_parameter_names = [reverse_parameter_names]
        for para in reverse_parameter_names:
            try:
                self.reverse_parameters.append(ForceData.forces_names.index(para))
            except:
                pass

        print((self.device_name, self.reverse_parameters))


class Sensor(DAQReadAnalog):
    SENSOR_CHANNELS = range(0, 5 + 1)  # channel 0:5 for FT sensor, channel 6
                                       # for trigger
    TRIGGER_CHANNELS = range(5, 6 + 1) # channel 7 for trigger
                                       # synchronization validation

    def __init__(self, settings):
        """ TODO"""

        super(Sensor, self).__init__(configuration=settings,
                               read_array_size_in_samples= \
                                   len(Sensor.SENSOR_CHANNELS) + len(
                                       Sensor.TRIGGER_CHANNELS))

        if self.DAQ_TYPE == "dummy":
            from ..daq._pyATIDAQ import DUMMY_ATI_CDLL
            self._atidaq = DUMMY_ATI_CDLL()
        else:
            # ATI voltage to forrce converter
            self._atidaq = ATI_CDLL()
            # get calibration
            index = ct.c_short(1)
            self._atidaq.createCalibration(settings.calibration_file, index)
            self._atidaq.setForceUnits("N")
            self._atidaq.setTorqueUnits("N-m")
        self.timer = Timer(sync_timer=settings.sync_timer)
        self._reverse_parameters = copy(settings.reverse_parameters)


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
        return ForceData(time = self.timer.time,
                         device_id = self.device_id,
                         forces = self._atidaq.convertToFT( voltages=read_buffer[Sensor.SENSOR_CHANNELS],
                                                            reverse_parameters=self._reverse_parameters),
                         trigger = read_buffer[Sensor.TRIGGER_CHANNELS].tolist())



class SensorProcess(Process):
    def __init__(self, settings, pipe_buffered_data_after_pause=True,
                  chunk_size=10000):
        """ForceSensorProcess

        return_buffered_data_after_pause: does not write shared data queue continuously and
            writes it the buffer data to queue only after pause (or stop)

        """

        # todo: docu explain usage

        # type checks
        if not isinstance(settings, SensorSettings):
            raise RuntimeError(
                "settings has to be force_sensor.Settings object")

        super(SensorProcess, self).__init__()
        self.sensor_settings = settings
        self._return_buffer = pipe_buffered_data_after_pause
        self._chunk_size = chunk_size

        self._pipe_i, self._pipe_o = Pipe()
        self._event_is_polling = Event()
        self._event_sending_data = Event()
        self._event_new_data = Event()
        self.event_bias_is_available = Event()
        self.event_trigger = Event()

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

    def get_force(self, parameter_id):
        if   parameter_id == 0: return self._last_Fx.value
        elif parameter_id == 1: return self._last_Fy.value
        elif parameter_id == 2: return self._last_Fz.value
        elif parameter_id == 3: return self._last_Tx.value
        elif parameter_id == 4: return self._last_Ty.value
        elif parameter_id == 5: return self._last_Tz.value
        else: return None

    def get_Fxyz(self):
        return (self._last_Fx.value, self._last_Fy.value, self._last_Fz.value)

    def Txyz(self):
        return (self._last_Tx.value, self._last_Ty.value, self._last_Tz.value)

    @property
    def sample_cnt(self):
        return self._sample_cnt.value

    def get_sample_cnt(self):
        return int(self._sample_cnt.value)

    def get_buffer_size(self):
        return int(self._buffer_size.value)

    def determine_bias(self, n_samples=100):  # TODO changing no samples. Does that work?
        """recording is paused after bias determination

        Bias determination is only possible while pause.
        This process might take a while. Please use "wait_bias_available" to
        ensure that the process is finished and the sensor is again read for
        recording.
        """

        if not self._event_is_polling.is_set():
            self._bias_n_samples = n_samples
            self.event_bias_is_available.clear()
            self._determine_bias_flag.set()

    def start_polling(self):
        self._event_is_polling.set()

    def pause_polling(self):
        self._event_is_polling.clear()

    def pause_polling_get_buffer(self):
        """pause polling and return recorded buffer"""
        self.pause_polling()
        sleep(0.1) # wait data acquisition paused properly
        rtn = []
        if self._event_sending_data.is_set() or self._buffer_size.value > 0:
            self._event_sending_data.wait()
            while self._buffer_size.value > 0:  # wait until buffer is empty
                rtn.extend(self._pipe_i.recv())
            self._event_sending_data.clear() # stop sending
        return rtn

    def stop(self):
        rtn = self.pause_polling_get_buffer()
        self.join()
        return rtn

    def join(self, timeout=None):
        if self._event_is_polling.is_set():
            self.pause_polling_get_buffer()
        self._event_stop_request.set()
        super(SensorProcess, self).join(timeout)


    def run(self):
        buffer = []
        self._buffer_size.value = 0
        sensor = Sensor(self.sensor_settings)
        self._event_is_polling.clear()
        self._event_sending_data.clear()
        is_polling = False
        while not self._event_stop_request.is_set():
            if self._event_is_polling.is_set():
                # is polling
                if not is_polling:
                    # start NI device and acquire one first dummy sample to
                    # ensure good timing
                    sensor.start_data_acquisition()
                    if self._return_buffer:
                        buffer.append(DAQEvents(time=sensor.timer.time,
                                    code="started:"+repr(sensor.device_id)))
                        self._buffer_size.value = len(buffer)
                    is_polling = True

                d = sensor.poll_force_data()
                self._last_Fx.value, self._last_Fy.value, self._last_Fz.value, \
				                     self._last_Tx.value, self._last_Ty.value, \
                                     self._last_Tz.value = d.forces
                self._sample_cnt.value += 1

                if self._return_buffer:
                    if self.event_trigger.is_set():
                        self.event_trigger.clear()
                        d.trigger[0] = 1

                    buffer.append(d)
                    self._buffer_size.value = len(buffer)

            else:
                # pause: not polling
                if is_polling:
                    if self._return_buffer:
                        buffer.append(DAQEvents(time=sensor.timer.time,
                                    code="pause:"+repr(sensor.device_id)))
                        self._buffer_size.value = len(buffer)
                    sensor.stop_data_acquisition()
                    is_polling = False

                if self._return_buffer and self._buffer_size.value>0:
                    # sending data to recorder
                    self._event_sending_data.set()
                    chks = self._chunk_size
                    while len(buffer)>0:
                        if chks > len(buffer):
                            chks = len(buffer)
                        self._pipe_o.send(buffer[0:chks])
                        buffer[0:chks] = []
                        self._buffer_size.value = len(buffer)
                    # wait that data are read
                    if self._event_sending_data.is_set():
                        sleep(0.01)

                if self._determine_bias_flag.is_set():
                    sensor.determine_bias(n_samples=self._bias_n_samples)
                    self._determine_bias_flag.clear()
                    self.event_bias_is_available.set()

                self._event_is_polling.wait(timeout=0.1)


        # stop process
        self._buffer_size.value = 0
        sensor.stop_data_acquisition()


"""Sensor History with moving average filtering and distance, velocity"""
class SensorHistory(object):
    """The Sensory History keeps track of the last n recorded sample and
    calculates online the moving average (running mean).

    SensorHistory.moving_average

    """

    def __init__(self, history_size, number_of_parameter):
        self.history = [[0] * number_of_parameter] * history_size
        self.moving_average = [0] * number_of_parameter
        self._correction_cnt = 0
        self._previous_moving_average = self.moving_average

    def __str__(self):
        return str(self.history)

    def update(self, values):
        """Update history and calculate moving average

        (correct for accumulated rounding errors ever 10000 samples)

        Parameter
        ---------
        values : list of values for all sensor parameters

        """

        self._previous_moving_average = self.moving_average
        pop = self.history.pop(0)
        self.history.append(values)
        # pop first element and calc moving average
        if self._correction_cnt > 10000:
            self._correction_cnt = 0
            self.moving_average = self.calc_history_average()
        else:
            self._correction_cnt += 1
            self.moving_average = list(map(
                lambda x: x[0] + (float(x[1] - x[2]) / len(self.history)),
                zip(self.moving_average, values, pop)))


    def calc_history_average(self):
        """Calculate history averages for all sensor parameter.

        The method is more time consuming than calling the property
        `moving_average`. It is does however not suffer from accumulated
        rounding-errors such as moving average.

        """

        s = [float(0)] * self.number_of_parameter
        for t in self.history:
            s = list(map(lambda x: x[0] + x[1], zip(s, t)))
        return list(map(lambda x: x / len(self.history), s))


    @property
    def history_size(self):
        return len(self.history)

    @property
    def number_of_parameter(self):
        return len(self.history[0])

    @property
    def previous_moving_average(self):
        return self._previous_moving_average


if __name__ == "__main__":
    #test sensor history
    import random
    from forceDAQ import Thresholds
    def run():
        sh = SensorHistory(history_size=5, number_of_parameter=3)
        thr = Thresholds([35, 20, 50, 80, 90])
        for x in range(1998):
            x = [random.randint(0, 10), random.randint(0, 100),
                    random.randint(0, 100)]
            sh.update(x)

        print(sh.moving_average, sh.calc_history_average())
        print(thr._thresholds)
        print(thr.get_level(80))

    import timeit
    print(timeit.timeit(run, number=1))
