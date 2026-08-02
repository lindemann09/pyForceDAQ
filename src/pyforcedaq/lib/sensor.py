"""Sensor class for reading data from NI devices and converting to force data.

Per default the NIDAQMX library is installed and access the NI instruments data.

Uses the atiiaftt library for converting voltages to force data, if installed.
"""

__author__ = "Oliver Lindemann"

from pathlib import Path

import atiiaftt
import numpy as np
from numpy.typing import NDArray

from ..constants import DaqType
from .clock import local_clock
from .daq import mock_daq, ni_daq
from .rec_tools import DataBuffer
from .settings import SensorSettings
from .types import ForceSensorData


class CalibrationConverter(object):  # type: ignore

    def __init__(self, calibration_file: str | Path):
        self._ftsensor = atiiaftt.FTSensor(str(calibration_file), index=1)

    def convertToFT(self, voltages:NDArray) -> list:
        return self._ftsensor.convertToFt(voltages.tolist()) #TODO: to list needed?

    def bias(self, bias_values: NDArray) -> None:
        self._ftsensor.bias(bias_values.tolist())

class Sensor(object):

    # channel 0:5 for FT sensor, channel 6  for trigger
    SENSOR_CHANNELS = range(0, 5 + 1)
    # channel 7 for trigger   synchronization validation
    TRIGGER_CHANNELS = range(5, 6 + 1) # TODO remove deprecated trigger channel support

    def __init__(self, s_settings: SensorSettings,
                 daq_type: DaqType,
                 buffer_size: int):
        """buffer_size: number of raw samples to keep in the buffer needed for determining the bias"""

        assert isinstance(s_settings, SensorSettings)
        assert len(self.SENSOR_CHANNELS) == len(ForceSensorData.forces_names)

        n_channels = len(self.SENSOR_CHANNELS) + len(self.TRIGGER_CHANNELS)
        if daq_type == DaqType.NIDAQMX:
            self.daq = ni_daq.DAQReadAnalog(configuration=s_settings,
                                     read_array_size_in_samples=n_channels)
        elif daq_type == DaqType.MOCK_SENSOR:
            self.daq = mock_daq.DAQReadAnalog(configuration=s_settings,
                                     read_array_size_in_samples=n_channels)
        else:
            raise RuntimeError(f"Unsupported daq_type: {daq_type}")

        if daq_type == DaqType.MOCK_SENSOR:
            self._calib_converter = None
        else:
            cal_file = s_settings.calibration_folder / s_settings.calibration_file_name
            self._calib_converter = CalibrationConverter(cal_file)

        self.sensor_id = s_settings.sensor_id
        self.device_label = s_settings.device_label
        self.convert_to_FT = s_settings.convert_to_FT

        self._reverse_vector = np.ones(len(ForceSensorData.forces_names))
        if s_settings.reverse_scaling is not None:
            if isinstance(s_settings.reverse_scaling, str):
                names = [s_settings.reverse_scaling]
            else:
                names = s_settings.reverse_scaling
            for para in names:
                try:
                    idx = ForceSensorData.forces_names.index(para)
                except ValueError:
                    continue
                self._reverse_vector[idx] = -1

        # for bias determination
        self.raw_sample_buffer = DataBuffer(maxlen=buffer_size) # unbiased samples
        self.bias = np.zeros(len(Sensor.SENSOR_CHANNELS), dtype=np.float64)

    def determine_bias(self):
        """determines bias based on the last raw samples"""

        self.bias = self.raw_sample_buffer.buffer_mean()
        if self._calib_converter is not None:
            self._calib_converter.bias(self.bias)

    def poll_data(self) -> list[ForceSensorData]:
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the calibration converter.

        Returns
        -------
        data: ForceSensorData
            the converted force data as ForceSensorData object

        """

        npdata_2d = self.daq.read_analog()
        t = local_clock()
        rtn = []
        for data in npdata_2d:

            raw_samples = data[Sensor.SENSOR_CHANNELS]
            self.raw_sample_buffer.append(raw_samples)

            # bias correction of raw samples and conversion to force data, if needed
            if self.convert_to_FT and self._calib_converter is not None:
                forces = np.asarray(
                    self._calib_converter.convertToFT(voltages=raw_samples)
                )
            else:
                # array
                forces = raw_samples - self.bias

            # reverse scaling if needed
            forces = forces * self._reverse_vector

            rtn.append(ForceSensorData(
                forces=forces,
                time=t,
                sensor_id=self.sensor_id,
                trigger=data[Sensor.TRIGGER_CHANNELS]
            )) # TODO: remove deprecated hardware trigger channel support

        return rtn