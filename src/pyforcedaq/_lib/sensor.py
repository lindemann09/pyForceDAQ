"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = 'Oliver Lindemann'

import ctypes as ct
from copy import copy

import numpy as np

from ..daq import ATI_CDLL, DAQReadAnalog
from .clock import local_clock
from .settings import SensorSettings
from .types import ForceSensorData


class Sensor(DAQReadAnalog):
    SENSOR_CHANNELS = range(0, 5 + 1)  # channel 0:5 for FT sensor, channel 6
                                       # for trigger
    TRIGGER_CHANNELS = range(5, 6 + 1) # channel 7 for trigger
                                       # synchronization validation

    def __init__(self, settings:SensorSettings):
        """ DOC"""

        assert(isinstance(settings, SensorSettings))

        super(Sensor, self).__init__(configuration=settings,
                               read_array_size_in_samples= \
                    len(Sensor.SENSOR_CHANNELS) + len(Sensor.TRIGGER_CHANNELS))

        self.device_id = settings.device_id
        self.name = settings.sensor_name
        self.convert_to_FT = settings.convert_to_FT
        if self.DAQ_TYPE == "mock_sensor":
            self._atidaq = None
            self.convert_to_FT = False
        else:
            # ATI voltage to force converter (DLL also required for biases)
            # TODO ATI_CDLL for biases mabye not needed for voltage recordings, check c-code
            self._atidaq = ATI_CDLL()

            # get calibration
            index = ct.c_short(1)
            self._atidaq.createCalibration(settings.calibration_file, index)
            self._atidaq.setForceUnits("N")
            self._atidaq.setTorqueUnits("N-m")

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

        if self._atidaq is not None:
            self._atidaq.bias(np.mean(data, axis=0))
            # not sure if bias required
            # for recoding of voltages, that is, not convert to forces

    def poll_data(self) -> ForceSensorData:
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the ATIDAO libraray.

        Returns
        -------
        data: ForceSensorData
            the converted force data as ForceSensorData object

        """

        start = local_clock()
        data, _read_samples = self.read_analog()
        if self.convert_to_FT:
            forces = self._atidaq.convertToFT( voltages=data[Sensor.SENSOR_CHANNELS],
                                                reverse_parameters=self._reverse_parameters)
        else:
            # array
            forces = list(data[Sensor.SENSOR_CHANNELS])
            for x in self._reverse_parameters:
                forces[x] = -1 * forces[x]
        t = local_clock()

        return ForceSensorData(time = t, acquisition_delay = t-start,
                         device_id = self.device_id,
                         forces = forces,
                         trigger = data[Sensor.TRIGGER_CHANNELS].tolist())

