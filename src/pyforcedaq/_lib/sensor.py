"""Sensor class for reading data from NI devices and converting to force data.

Per default the NIDAQMX library is installed and access the NI instruments data.
If the PyDAQMX library is installed, this library is used instead.

For conversion to force data, the ATI dll will be used (use_aiftt=True, DEFAULT). Alternatively, you
might use your own complied dll and pyforceDAQ own interface to the DLL (use_aiftt=False)
"""

__author__ = "Oliver Lindemann"

from collections import deque

import numpy as np

from .. import constants
from ..constants import DaqType
from .clock import local_clock
from .settings import SensorSettings
from .types import ForceSensorData


class Sensor(object):

    # channel 0:5 for FT sensor, channel 6  for trigger
    SENSOR_CHANNELS = range(0, 5 + 1)
    # channel 7 for trigger   synchronization validation
    TRIGGER_CHANNELS = range(5, 6 + 1)

    def __init__(self, s_settings: SensorSettings,
                 daq_type: DaqType,
                 buffer_size: int,
                 use_aiftt: bool=True):
        """buffer_size: number of raw samples to keep in the buffer needed for determining the bias"""

        assert isinstance(s_settings, SensorSettings)
        assert len(self.SENSOR_CHANNELS) == len(ForceSensorData.forces_names)

        if daq_type == DaqType.NIDAQMX:
            from ..daq.read_daq_nidaqmx import DAQReadAnalog
        elif daq_type == DaqType.PYDAQMX:
            from ..daq.read_daq_pydaqmx import DAQReadAnalog
        elif daq_type == DaqType.MOCK_SENSOR:
            from ..daq.read_daq_mock_sensor import DAQReadAnalog
        else:
            raise RuntimeError(f"Unsupported daq_type: {daq_type}")

        if use_aiftt:
            from ..daq.calibration_iaftt import CalibrationConverter
        else:
            from ..daq.calibration_dll import CalibrationConverter

        self.daq = DAQReadAnalog(configuration=s_settings,
            read_array_size_in_samples=len(Sensor.SENSOR_CHANNELS)
            + len(Sensor.TRIGGER_CHANNELS))

        if daq_type == DaqType.MOCK_SENSOR:
            self._calib_converter = None
        else:
            self._calib_converter = CalibrationConverter(s_settings.calibration_file)

        self.sensor_id = s_settings.sensor_id
        self.device_label = s_settings.device_label
        self.convert_to_FT = s_settings.convert_to_FT

        self._reverse_vector = np.ones(len(ForceSensorData.forces_names))
        if s_settings.reverse_parameter_names is not None:
            if isinstance(s_settings.reverse_parameter_names, str):
                names = [s_settings.reverse_parameter_names]
            else:
                names = s_settings.reverse_parameter_names
            for para in names:
                try:
                    idx = ForceSensorData.forces_names.index(para)
                except ValueError:
                    continue
                self._reverse_vector[idx] = -1

        # for bias determination
        self._raw_sample_buffer = deque(maxlen=buffer_size)
        self.bias = np.zeros(len(Sensor.SENSOR_CHANNELS), dtype=np.float64)

    def determine_bias(self):
        """determines bias based on the last raw samples"""

        self.bias = np.mean(self._raw_sample_buffer, axis=0)
        if self._calib_converter is not None:
            self._calib_converter.bias(self.bias)

    # def determine_bias_old(self, n_samples=100): ## FIXME not needed
    #     """determines the bias"""

    #     task_was_running = self.daq.is_acquiring_data
    #     self.daq.start_data_acquisition()
    #     data = None
    #     for _ in range(n_samples):
    #         read_buffer, _ = self.daq.read_analog()
    #         sample = read_buffer[Sensor.SENSOR_CHANNELS]
    #         if data is None:
    #             data = sample
    #         else:
    #             data = np.vstack((data, sample))

    #     if not task_was_running:
    #         self.daq.stop_data_acquisition()

    #     if self._calib_converter is not None and isinstance(data, np.ndarray):
    #         self._calib_converter.bias(np.mean(data, axis=0))
    #         # not sure if bias required
    #         # for recoding of voltages, that is, not convert to forces

    def poll_data(self) -> ForceSensorData:
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the calibration converter.

        Returns
        -------
        data: ForceSensorData
            the converted force data as ForceSensorData object

        """

        data, _ = self.daq.read_analog()
        raw_samples = data[Sensor.SENSOR_CHANNELS]
        self._raw_sample_buffer.append(raw_samples)

        t = local_clock()
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

        return ForceSensorData(
            time=t,
            sensor_id=self.sensor_id,
            forces=forces,
            trigger=data[Sensor.TRIGGER_CHANNELS]
        )