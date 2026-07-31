__author__ = "Oliver Lindemann"

import atexit
import ctypes as ct
import logging
from multiprocessing import Array, Event, Process, Queue, Value
from typing import Optional

import numpy as np
from numpy import typing as npt

from ..constants import DaqType
from . import lsl
from .sensor import Sensor
from .settings import RecordingSettings, SensorSettings


class SensorProcess(Process):

    DETERMINE_BIAS_SAMPLES = 20
    INIT_SAMPLES = 100

    def __init__(
        self,
        sensor_settings: SensorSettings,
        recording_settings: RecordingSettings,
        file_writer_queue: Optional[Queue],
        daq_type: DaqType
    ):
        """ForceSensorProcess

        return_buffered_data_after_pause: does not write shared data queue continuously and
            writes it the buffer data to queue only after pause (or stop)

        """

        # DOC explain usage

        # type checks
        if not isinstance(sensor_settings, SensorSettings):
            raise RuntimeError("sensor_settings has to be force_sensor settings object")
        if not isinstance(recording_settings, RecordingSettings):
            raise RuntimeError(
                "recording_settings has to be force_sensor.RecordingSettings object"
            )

        super(SensorProcess, self).__init__()

        self._daq_type = daq_type
        self.sensor_settings = sensor_settings
        self.recording_settings = recording_settings
        self._file_writer_queue = file_writer_queue

        self.event_trigger = Event()  #  software trigger

        self._dat = Array(ct.c_double, 6)
        self._np_dat = np.frombuffer(
            self._dat.get_obj(), dtype=np.float64
        )  # numpy view
        self._saved_sample_cnt = Value(ct.c_int64, 0)
        self._total_sample_cnt = Value(ct.c_int64, 0)
        self.flag_sensor_bias_is_determined = Event()
        self._flag_quit_request = Event()
        self.__flag_is_saving = Event()

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
        return self._saved_sample_cnt.value

    def get_total_sample_cnt(self) -> int:
        return self._total_sample_cnt.value

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
        sensor = Sensor(self.sensor_settings,
                        daq_type=self._daq_type,
                        buffer_size=SensorProcess.DETERMINE_BIAS_SAMPLES)

        stream_forces = self.recording_settings.array_write_forces()
        stream_trigger = self.recording_settings.array_write_trigger()

        ## create init LSL
        lsl_data_steam = None
        lsl_hardware_trigger_stream = None
        if self.recording_settings.lsl_stream:
            lsl_data_steam = lsl.init_stream(
                name=f"Force_{sensor.device_label}",
                content_type="force",
                n_channels=sum(stream_forces),
                stream_id=f"RF_{sensor.device_label}",
                freq=self.sensor_settings.rate,
                channel_format=lsl.cf_double64,
                metadata={"sensor_label": self.sensor_settings.device_label},
            )

            n_hardware_trigger = sum(stream_trigger)
            if n_hardware_trigger > 0:
                lsl_hardware_trigger_stream = lsl.init_stream(
                    name=f"Trigger_{sensor.device_label}",
                    content_type="Marker",
                    n_channels=n_hardware_trigger,
                    stream_id=f"Tr_{sensor.device_label}",
                    channel_format=lsl.cf_double64,
                    freq=self.sensor_settings.rate,
                )

        sensor.daq.start_data_acquisition()
        logging.info(
            "Sensor start, %s, pid %s",
            sensor.device_label,
            self.pid
        )
        # FIXME logging is inconsistent, check logging and console output

        # polling loop
        self.pause_saving()
        self._flag_quit_request.clear()
        self.flag_sensor_bias_is_determined.clear()
        init_samples = SensorProcess.INIT_SAMPLES

        while not self._flag_quit_request.is_set():

            data = sensor.poll_data()
            for d in data:
                if self.event_trigger.is_set():
                    self.event_trigger.clear()
                    d.trigger[0] = 1 # FIXME LSL marker stream

                if init_samples > 0:
                    # initial samples that are used and merely used bias determination, do not write to LSL or file writer queue
                    init_samples -= 1
                    if init_samples <= 0:
                        sensor.determine_bias()
                    continue

                ## LSL
                if lsl_data_steam is not None:
                    lsl_data_steam.push_sample(d.forces[stream_forces])
                if lsl_hardware_trigger_stream is not None:
                    tr = d.trigger[stream_trigger]
                    if any(tr):  # only stream if at least one trigger is active
                        lsl_hardware_trigger_stream.push_sample(tr)

                # write to shared memory and file writer queue
                self._total_sample_cnt.value += 1 # type: ignore
                self._dat[:] = d.forces

                if self.is_saving() and self._file_writer_queue is not None:
                    self._file_writer_queue.put(d)
                    self._saved_sample_cnt.value += 1  # type: ignore # TODO check if all the sample counter are needed

                if not self.flag_sensor_bias_is_determined.is_set():
                    # new baseline requested
                    sensor.determine_bias()
                    self.flag_sensor_bias_is_determined.set()

        # stop process
        self.pause_saving()
        sensor.daq.stop_data_acquisition()
        logging.info("Sensor quit, %s", sensor.device_label)

