"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = 'Oliver Lindemann'

import ctypes as ct
from copy import copy
import numpy as np

from ..daq import ATI_CDLL, DAQConfiguration,  DAQReadAnalog
from .._lib.misc import find_calibration_file
from .._lib.types import ForceData
from .._lib.timer import Timer, app_timer

class SensorSettings(DAQConfiguration):
    def __init__(self,
                 device_id,
                 sensor_name,
                 calibration_folder,
                 channels="ai0:7",
                 device_name_prefix = "Dev",
                 rate=1000,
                 minVal=-10,
                 maxVal=10,
                 reverse_parameter_names=(),
                 convert_to_FT=True):

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
        self.device_id = device_id
        self.sensor_name = sensor_name
        self.convert_to_FT = convert_to_FT
        if self.convert_to_FT:
            self.calibration_file = find_calibration_file(
                                        calibration_folder=calibration_folder,
                                        sensor_name=sensor_name)
        else:
            self.calibration_file = None

        self.reverse_parameters = []
        if not isinstance(reverse_parameter_names, (tuple, list)):
            reverse_parameter_names = [reverse_parameter_names]
        for para in reverse_parameter_names:
            try:
                self.reverse_parameters.append(ForceData.forces_names.index(para))
            except:
                pass


class Sensor(DAQReadAnalog):
    SENSOR_CHANNELS = range(0, 5 + 1)  # channel 0:5 for FT sensor, channel 6
                                       # for trigger
    TRIGGER_CHANNELS = range(5, 6 + 1) # channel 7 for trigger
                                       # synchronization validation

    def __init__(self, settings):
        """ DOC"""

        assert(isinstance(settings, SensorSettings))

        super(Sensor, self).__init__(configuration=settings,
                               read_array_size_in_samples= \
                    len(Sensor.SENSOR_CHANNELS) + len(Sensor.TRIGGER_CHANNELS))

        self.device_id = settings.device_id
        self.name = settings.sensor_name
        self.convert_to_FT = settings.convert_to_FT
        self.timer = Timer(sync_timer=app_timer) # own timer, because this
        # class is used in own process
        if self.DAQ_TYPE == "dummy":
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

    def poll_data(self):
        """Polling data

        Reading data from NI device and converting voltages to force data using
        the ATIDAO libraray.

        Returns
        -------
        data: ForceData
            the converted force data as ForceData object

        """

        start = self.timer.time
        read_buffer, _read_samples = self.read_analog()
        if self.convert_to_FT:
            forces = self._atidaq.convertToFT( voltages=read_buffer[Sensor.SENSOR_CHANNELS],
                                                reverse_parameters=self._reverse_parameters)
        else:
            # array
            forces = list(read_buffer[Sensor.SENSOR_CHANNELS])

        for x in self._reverse_parameters:
            forces[x] = -1 * forces[x]

        t = self.timer.time
        return ForceData(time = t, acquisition_delay = t-start,
                         device_id = self.device_id,
                         forces = forces,
                         trigger = read_buffer[Sensor.TRIGGER_CHANNELS].tolist())


if __name__ == "__main__":
    #test sensor history
    import random
    from forceDAQ import Thresholds
    from forceDAQ._lib.misc import SensorHistory
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
