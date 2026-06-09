__author__ = "Oliver Lindemann"

import atexit
import ctypes as ct
import logging
from collections import deque
from multiprocessing import Array, Event, Process, Queue, Value
from typing import Optional

import numpy as np
from numpy import typing as npt

from .. import constants
from .lsl import LSLSream, cf_float32
from .process_priority_manager import get_priority
from .sensor import Sensor
from .settings import RecordingSettings, SensorSettings

DETERMINE_BIAS_SAMPLES = 100

class SensorProcess(Process):

    def __init__(
        self,
        sensor_settings: SensorSettings,
        recording_settings: RecordingSettings,
        file_writer_queue: Optional[Queue],
        daq_type: int,
        use_aiftt: bool
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
        self._file_writer_queue = file_writer_queue

        self.event_trigger = Event()  #  software trigger

        self._dat = Array(ct.c_double, 6)
        self._np_dat = np.frombuffer(
            self._dat.get_obj(), dtype=np.float64
        )  # numpy view
        self._sample_cnt = Value(ct.c_int64, 0)
        self.flag_sensor_bias_is_determined = Event()
        self._flag_quit_request = Event()
        self.__flag_is_saving = Event()

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

    def get_saved_sample_cnt(self) -> int:
        return self._sample_cnt.value

    def determine_bias(self):
        self.flag_sensor_bias_is_determined.clear()

    def start_saving(self):
        if self._file_writer_queue is not None:
            self.__flag_is_saving.set()

    def pause_saving(self):
        self.__flag_is_saving.clear()

    def is_saving(self) -> bool:
        return self.__flag_is_saving.is_set()

    def quit(self):
        self._flag_quit_request.set()

    def join(self, timeout=None):
        self._flag_quit_request.set()
        super(SensorProcess, self).join(timeout)

    def run(self):
        fifo = deque(maxlen=DETERMINE_BIAS_SAMPLES)
        sensor = Sensor(self.sensor_settings,
                        daq_type=self._daq_type,
                        use_aiftt=self._use_aiftt)

        stream_forces = self.recording_settings.array_write_forces()
        stream_trigger = self.recording_settings.array_write_trigger()

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

        sensor.daq.start_data_acquisition()
        logging.info(
            "Sensor start, %s, pid %s, priority %s",
            sensor.device_label,
            self.pid,
            get_priority(self.pid),
        )

        # polling loop
        self.pause_saving()
        self._flag_quit_request.clear()
        self.flag_sensor_bias_is_determined.clear()
        init_samples = DETERMINE_BIAS_SAMPLES * 2

        while not self._flag_quit_request.is_set():

            d = sensor.poll_data()
            if self.event_trigger.is_set():
                self.event_trigger.clear()
                d.trigger[0] = 1 # FIXME LSL marker stream

            if init_samples > 0:
                # initial samples for bias determination, do not write to LSL or file writer queue
                init_samples -= 1
                fifo.append(d.forces)
                if init_samples == 0:
                    sensor.set_bias(np.array(fifo))
                    self.flag_sensor_bias_is_determined.set()
                continue

            ## LSL
            if lsl_data_steam.is_init:
                # stream only select forces
                lsl_data_steam.outlet.push_sample(d.forces[stream_forces])  # type: ignore
            if lsl_hardware_trigger_stream.is_init:
                tr = d.trigger[stream_trigger]
                if any(tr):  # only stream if at least one trigger is active
                    lsl_hardware_trigger_stream.outlet.push_sample(tr)  # type: ignore

            # write to shared memory and file writer queue
            self._dat[:] = d.forces
            fifo.append(d.forces) # for bias determination

            if self.is_saving() and self._file_writer_queue is not None:
                self._file_writer_queue.put(d)
                self._sample_cnt.value += 1  # type: ignore

            if not self.flag_sensor_bias_is_determined.is_set():
                # new baseline requested
                sensor.set_bias(np.array(fifo))
                self.flag_sensor_bias_is_determined.clear()
                # FIXME determine bias marker event?

        # stop process
        self.pause_saving()
        sensor.daq.stop_data_acquisition()
        logging.info("Sensor quit, %s", sensor.device_label)

# FIXME check trigger processing and UDP connections
