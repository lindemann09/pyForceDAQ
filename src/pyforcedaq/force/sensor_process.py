__author__ = 'Oliver Lindemann'

import atexit
import ctypes as ct
import logging
from multiprocessing import Event, Pipe, Process, sharedctypes

from .._lib import lsl, timer
from .._lib.polling_time_profile import PollingTimeProfile
from .._lib.process_priority_manager import get_priority
from .._lib.types import DAQEvents
from .sensor import Sensor, SensorSettings


class SensorProcess(Process):

    def __init__(self, settings, pipe_buffered_data_after_pause=True,
                  chunk_size=10000):
        """ForceSensorProcess

        return_buffered_data_after_pause: does not write shared data queue continuously and
            writes it the buffer data to queue only after pause (or stop)

        """

        # DOC explain usage

        # type checks
        if not isinstance(settings, SensorSettings):
            raise RuntimeError(
                "settings has to be force_sensor.Settings object")

        super(SensorProcess, self).__init__()
        self.sensor_settings = settings
        self._pipe_buffer_after_pause = pipe_buffered_data_after_pause
        self._chunk_size = chunk_size

        self._pipe_i, self._pipe_o = Pipe()
        self._event_is_polling = Event()
        self._event_sending_data = Event()
        self._event_new_data = Event()
        self.event_bias_is_available = Event()
        self.event_trigger = Event()  #  software trigger

        self._last_Fx = sharedctypes.RawValue(ct.c_float)
        self._last_Fy = sharedctypes.RawValue(ct.c_float)
        self._last_Fz = sharedctypes.RawValue(ct.c_float)
        self._last_Tx = sharedctypes.RawValue(ct.c_float)
        self._last_Ty = sharedctypes.RawValue(ct.c_float)
        self._last_Tz = sharedctypes.RawValue(ct.c_float)
        self._buffer_size = sharedctypes.RawValue(ct.c_uint64)
        self._sample_cnt = sharedctypes.Value(ct.c_uint64)
        self._event_quit_request = Event()
        self._determine_bias_flag = Event()

        self._bias_n_samples = 200
        atexit.register(self.join)

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

    def get_sample_cnt(self):
        return int(self._sample_cnt.value)

    def get_buffer_size(self):
        return int(self._buffer_size.value)

    def determine_bias(self, n_samples=100):
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

    def get_buffer(self, timeout=1.0):
        """return recorded buffer"""
        rtn = []
        if self._event_sending_data.is_set() or self._buffer_size.value > 0:
            self._event_sending_data.wait()
            while self._buffer_size.value > 0:  # wait until buffer is empty
                rtn.extend(self._pipe_i.recv())
            self._event_sending_data.clear() # stop sending
        return rtn

    def join(self, timeout=None):

        if self._event_is_polling.is_set():
            self.pause_polling()
            timer.wait(100)
            self.get_buffer() # empty buffer, required to quit process run loop

        self._event_quit_request.set()
        super(SensorProcess, self).join(timeout)


    def run(self):
        buffer = []
        self._buffer_size.value = 0
        sensor = Sensor(self.sensor_settings)
        stream_forces = self.sensor_settings.array_write_forces()
        stream_trigger = self.sensor_settings.array_write_trigger()

        self._event_is_polling.clear()
        self._event_sending_data.clear()
        is_polling = False
        ptp = PollingTimeProfile() #TODO just for testing?

        ## create init LSL
        lsl_data_steam = None
        lsl_hardware_trigger_stream = None
        if self.sensor_settings.has_lsl_stream:
            lsl_data_steam = lsl.init(
                    name=f"Force {self.sensor_settings.device_name}",
                    n_channels=sum(stream_forces),
                    stream_id=f"RF_{self.sensor_settings.device_name}",
                    freq=self.sensor_settings.rate,
                    metadata={"sensor_name": self.sensor_settings.sensor_name})
            n_hardware_trigger = sum(stream_trigger)
            if n_hardware_trigger > 0:
                lsl_hardware_trigger_stream = lsl.init(
                    name=f"Trigger {self.sensor_settings.device_name}",
                    n_channels=n_hardware_trigger,
                    stream_id=f"Tr_{self.sensor_settings.device_name}",
                    freq=self.sensor_settings.rate)


        while not self._event_quit_request.is_set():
            if self._event_is_polling.is_set():
                # is polling
                if not is_polling:
                    # start NI device and acquire one first sample to
                    # ensure good timing
                    sensor.start_data_acquisition()
                    buffer.append(DAQEvents(time=sensor.timer.time,
                                            code="started:"+repr(sensor.device_id)))
                    logging.info("Sensor start, name %s, pid %s, priority %s",
                        sensor.name,self.pid, get_priority(self.pid))
                    is_polling = True

                d = sensor.poll_data()
                ## LSL
                if lsl_data_steam is not None:
                    lsl_data_steam.push_sample(list(d.selected_forces(stream_forces))) # steam only select forces
                if lsl_hardware_trigger_stream is not None:
                    lsl_hardware_trigger_stream.push_sample(list(d.selected_trigger(stream_trigger))) # stream only triggers

                ptp.update(d.time) # needed? TODO
                self._last_Fx.value, self._last_Fy.value, self._last_Fz.value, \
				                     self._last_Tx.value, self._last_Ty.value, \
                                     self._last_Tz.value = d.forces
                self._sample_cnt.value += 1

                if self.event_trigger.is_set():
                    self.event_trigger.clear()
                    d.trigger[0] = 1

                buffer.append(d)
                self._buffer_size.value = len(buffer)

            else:
                # pause: not polling
                if is_polling:
                    sensor.stop_data_acquisition()
                    buffer.append(DAQEvents(time=sensor.timer.time,
                                            code="pause:"+repr(sensor.device_id)))
                    self._buffer_size.value = len(buffer)
                    logging.info(
                        "Sensor stop, name %s, pid %s, priority %s",
                        sensor.name,
                        self.pid,
                        get_priority(self.pid),
                    )
                    is_polling = False
                    ptp.stop()

                if self._pipe_buffer_after_pause and self._buffer_size.value>0:
                    # sending data to force
                    self._event_sending_data.set()
                    chks = self._chunk_size
                    while len(buffer)>0:
                        if chks > len(buffer):
                            chks = len(buffer)
                        self._pipe_o.send(buffer[0:chks])
                        buffer[0:chks] = [] # clear buffer
                        self._buffer_size.value = len(buffer)

                    while self._event_sending_data.is_set():
                        timer.wait(2)

                if self._determine_bias_flag.is_set():
                    sensor.determine_bias(n_samples=self._bias_n_samples)
                    self._determine_bias_flag.clear()
                    self.event_bias_is_available.set()

                self._event_is_polling.wait(timeout=0.1)


        # stop process
        sensor.stop_data_acquisition()
        self._buffer_size.value = 0

        logging.info("Sensor quit, %s, %s", sensor.name, ptp.get_profile_str())
