__author__ = "Oliver Lindemann"

import atexit
import ctypes as ct
import logging
from multiprocessing import Array, Event, Pipe, Process, Value

import numpy as np
from numpy import typing as npt

from .. import constants
from .clock import local_clock, wait_ms
from .lsl import LSLSream, cf_float32
from .polling_time_profile import PollingTimeProfile
from .process_priority_manager import get_priority
from .sensor import Sensor
from .settings import RecordingSettings, SensorSettings
from .types import DAQEvents


class SensorProcess(Process):
    def __init__(
        self,
        sensor_settings: SensorSettings,
        recording_settings: RecordingSettings,
        daq_type: int,
        use_aiftt: bool,
        pipe_buffered_data_after_pause=True,
        chunk_size=10000,
    ):
        """ForceSensorProcess

        return_buffered_data_after_pause: does not write shared data queue continuously and
            writes it the buffer data to queue only after pause (or stop)

        """

        # DOC explain usage

        # type checks
        if not isinstance(sensor_settings, SensorSettings):
            raise RuntimeError("sensor_settings has to be force_sensor.Settings object")
        if not isinstance(recording_settings, RecordingSettings):
            raise RuntimeError(
                "recording_settings has to be force_sensor.RecordingSettings object"
            )

        super(SensorProcess, self).__init__()

        if daq_type not in [constants.NIDAQMX, constants.PYDAQMX, constants.MOCK_SENSOR]:
            raise RuntimeError(f"Unsupported daq_type: {daq_type}")

        self._daq_type = daq_type
        self._use_aiftt = use_aiftt
        self.sensor_settings = sensor_settings
        self.recording_settings = recording_settings
        self._pipe_buffer_after_pause = pipe_buffered_data_after_pause
        self._chunk_size = chunk_size

        self._pipe_i, self._pipe_o = Pipe()
        self._event_is_polling = Event()
        self._event_sending_data = Event()
        self._event_new_data = Event()
        self.event_bias_is_available = Event()
        self.event_trigger = Event()  #  software trigger

        self._dat = Array(ct.c_double, 6)
        self._np_dat = np.frombuffer(
            self._dat.get_obj(), dtype=np.float64
        )  # numpy view
        self._buffer_size = Value(ct.c_int64, 0)
        self._sample_cnt = Value(ct.c_int64, 0)
        self._event_quit_request = Event()
        self._determine_bias_flag = Event()

        self._bias_n_samples = 200
        atexit.register(self.join)

    @property
    def Fx(self) -> float:
        return self._dat[0]

    @property
    def Fy(self) -> float:
        return self._dat[1]

    @property
    def Fz(self) -> float:
        return self._dat[2]

    @property
    def Tx(self) -> float:
        return self._dat[3]

    @property
    def Ty(self) -> float:
        return self._dat[4]

    @property
    def Tz(self) -> float:
        return self._dat[5]

    def get_force(self, parameter_id) -> float | None:
        if parameter_id < 0 or parameter_id > 5:
            return None
        else:
            return self._dat[parameter_id]

    def get_Fxyz(self) -> npt.NDArray[np.float64]:
        return self._np_dat[0:3]

    def Txyz(self) -> npt.NDArray[np.float64]:
        return self._np_dat[3:6]

    def get_sample_cnt(self) -> int:
        return self._sample_cnt.value

    def get_buffer_size(self) -> int:
        return self._buffer_size.value

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
            self._event_sending_data.clear()  # stop sending
        return rtn

    def join(self, timeout=None):

        if self._event_is_polling.is_set():
            self.pause_polling()
            wait_ms(100)
            self.get_buffer()  # empty buffer, required to quit process run loop

        self._event_quit_request.set()
        super(SensorProcess, self).join(timeout)

    def run(self):
        buffer = []
        self._buffer_size.value = 0
        sensor = Sensor(self.sensor_settings,
                        daq_type=self._daq_type,
                        use_aiftt=self._use_aiftt)

        stream_forces = self.recording_settings.array_write_forces()
        stream_trigger = self.recording_settings.array_write_trigger()

        self._event_is_polling.clear()
        self._event_sending_data.clear()
        is_polling = False
        ptp = PollingTimeProfile()  # TODO just for testing?

        ## create init LSL
        lsl_data_steam = LSLSream()
        lsl_hardware_trigger_stream = LSLSream()
        if self.recording_settings.lsl_stream:
            lsl_data_steam.init(
                name=f"Force_{sensor.device_label}",
                n_channels=sum(stream_forces),
                stream_id=f"RF_{sensor.device_label}",
                freq=self.sensor_settings.rate,
                channel_format=cf_float32,
                metadata={"sensor_label": self.sensor_settings.device_label},
            )

            n_hardware_trigger = sum(stream_trigger)
            if n_hardware_trigger > 0:
                lsl_hardware_trigger_stream.init(
                    name=f"Trigger_{sensor.device_label}",
                    n_channels=n_hardware_trigger,
                    stream_id=f"Tr_{sensor.device_label}",
                    channel_format=cf_float32,
                    freq=self.sensor_settings.rate,
                )

        while not self._event_quit_request.is_set():
            if self._event_is_polling.is_set():
                # is polling
                if not is_polling:
                    # start NI device and acquire one first sample to
                    # ensure good timing
                    sensor.daq.start_data_acquisition()
                    buffer.append(
                        DAQEvents(
                            time=local_clock(), code="started:" + sensor.device_label
                        )
                    )
                    logging.info(
                        "Sensor start, %s, pid %s, priority %s",
                        sensor.device_label,
                        self.pid,
                        get_priority(self.pid),
                    )
                    is_polling = True

                d = sensor.poll_data()

                ## LSL
                if lsl_data_steam.is_init:
                    # stream only select forces
                    lsl_data_steam.outlet.push_sample(d.forces[stream_forces])  # type: ignore
                if lsl_hardware_trigger_stream.is_init:
                    tr = d.trigger[stream_trigger]
                    if any(tr):  # only stream if at least one trigger is active
                        lsl_hardware_trigger_stream.outlet.push_sample(tr)  # type: ignore

                ptp.update(d.time)  # needed? TODO
                self._dat[:] = d.forces
                self._sample_cnt.value += 1  # type: ignore

                if self.event_trigger.is_set():
                    self.event_trigger.clear()
                    d.trigger[0] = 1

                if self.recording_settings.save_data:
                    buffer.append(d)
                    self._buffer_size.value = len(buffer)

            else:
                # pause: not polling
                if is_polling:
                    sensor.daq.stop_data_acquisition()
                    buffer.append(
                        DAQEvents(
                            time=local_clock(), code="pause:" + sensor.device_label
                        )
                    )
                    self._buffer_size.value = len(buffer)
                    logging.info(
                        "Sensor stop,  %s, pid %s, priority %s",
                        sensor.device_label,
                        self.pid,
                        get_priority(self.pid),
                    )
                    is_polling = False
                    ptp.stop()

                if self._pipe_buffer_after_pause and self._buffer_size.value > 0:
                    # sending data to force
                    self._event_sending_data.set()
                    chks = self._chunk_size
                    while len(buffer) > 0:
                        if chks > len(buffer):
                            chks = len(buffer)
                        self._pipe_o.send(buffer[0:chks])
                        buffer[0:chks] = []  # clear buffer
                        self._buffer_size.value = len(buffer)

                    while self._event_sending_data.is_set():
                        wait_ms(2)

                if self._determine_bias_flag.is_set():
                    sensor.determine_bias(n_samples=self._bias_n_samples)
                    self._determine_bias_flag.clear()
                    self.event_bias_is_available.set()

                self._event_is_polling.wait(timeout=0.1)

        # stop process
        sensor.daq.stop_data_acquisition()
        self._buffer_size.value = 0

        logging.info("Sensor quit, %s, %s", sensor.device_label, ptp.get_profile_str())


# FIXME check trigger processing and UDP connections#FIXME check trigger processing and UDP connections
