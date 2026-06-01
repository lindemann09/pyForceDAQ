"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import numpy as np

from .. import daq
from .clock import local_clock
from .settings import SensorSettings
from .types import ForceSensorData


class Sensor(object):
    # channel 0:5 for FT sensor, channel 6  for trigger
    SENSOR_CHANNELS = range(0, 5 + 1)
    # channel 7 for trigger   synchronization validation
    TRIGGER_CHANNELS = range(5, 6 + 1)

    def __init__(self, s_settings: SensorSettings,
                 daq_type: int,
                 use_aiftt: bool):
        """DOC"""

        assert isinstance(s_settings, SensorSettings)
        assert len(self.SENSOR_CHANNELS) == len(ForceSensorData.forces_names)

        if daq_type == daq.NIDAQMX:
            from ..daq.read_daq_nidaqmx import DAQReadAnalog
        elif daq_type == daq.PYDAQMX:
            from ..daq.read_daq_pydaqmx import DAQReadAnalog
        elif daq_type == daq.MOCK_SENSOR:
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

        if daq_type == daq.MOCK_SENSOR:
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

    def determine_bias(self, n_samples=100):
        """determines the bias"""

        task_was_running = self.daq.is_acquiring_data
        self.daq.start_data_acquisition()
        data = None
        for _ in range(n_samples):
            read_buffer, _ = self.daq.read_analog()
            sample = read_buffer[Sensor.SENSOR_CHANNELS]
            if data is None:
                data = sample
            else:
                data = np.vstack((data, sample))

        if not task_was_running:
            self.daq.stop_data_acquisition()

        if self._calib_converter is not None and isinstance(data, np.ndarray):
            self._calib_converter.bias(np.mean(data, axis=0))
            # not sure if bias required
            # for recoding of voltages, that is, not convert to forces

    def poll_data(self) -> ForceSensorData:
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the calibration converter.

        Returns
        -------
        data: ForceSensorData
            the converted force data as ForceSensorData object

        """

        start = local_clock()
        data, _read_samples = self.daq.read_analog()
        if self.convert_to_FT and self._calib_converter is not None:
            forces = np.asarray(
                self._calib_converter.convertToFT(voltages=data[Sensor.SENSOR_CHANNELS])
            )
        else:
            # array
            forces = data[Sensor.SENSOR_CHANNELS]

        # reverse scaling if needed
        forces = forces * self._reverse_vector
        t = local_clock()

        return ForceSensorData(
            time=t,
            acquisition_delay=t - start,
            sensor_id=self.sensor_id,
            forces=forces,
            trigger=data[Sensor.TRIGGER_CHANNELS],
        )