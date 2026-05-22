import nidaqmx
import numpy as np
from nidaqmx import constants as nidaq_consts

from . import DAQConfiguration


class DAQReadAnalog(nidaqmx.Task):

    NUM_SAMPS_PER_CHAN = nidaq_consts.READ_ALL_AVAILABLE # or 1 FIXME?
    TIMEOUT = 1.0
    DAQ_TYPE = "nidaqmx"

    def __init__(self, configuration: DAQConfiguration, read_array_size_in_samples: int):
        """ DOC
        read_array_size_in_samples for ReadAnalogF64 call

        """

        nidaqmx.Task.__init__(self)

        # CreateAIVoltageChan
        self.ai_channels.add_ai_voltage_chan(physical_channel=configuration.physicalChannel,
                            terminal_config=nidaq_consts.TerminalConfiguration.DIFF,
                            min_val=configuration.minVal,
                            max_val=configuration.maxVal,
                            units=nidaq_consts.VoltageUnits.VOLTS
                            )
        print('added channels')
        #CfgSampClkTiming
        self.timing.cfg_samp_clk_timing(rate=float(configuration.rate),
                            active_edge=nidaq_consts.Edge.RISING,
                            sample_mode=nidaq_consts.AcquisitionType.CONTINUOUS
                            )
        print('devices')
        print(nidaqmx.Task.devices)
        self._task_is_started = False
        self.read_array_size_in_samples = read_array_size_in_samples

    @property
    def is_acquiring_data(self):
        return self._task_is_started

    def start_data_acquisition(self):
        """Start data acquisition of the NI device
        call always before polling

        """

        if not self._task_is_started:
            self.start()
            self._task_is_started = True

    def stop_data_acquisition(self):
        """ Stop data acquisition of the NI device
        """

        if self._task_is_started:
            self.stop()
            self._task_is_started = False

    def read_analog(self):
        """Polling data

        Reading data from NI device

        Parameter
        ---------
        array_size_in_samps : int
            the array size in number of samples

        Returns
        -------
        read_buffer : numpy array
            the read data
        read_samples : int
            the number of read samples

        """

        #fill in data
        data = self.read(self.NUM_SAMPS_PER_CHAN, self.TIMEOUT)
        np_data = np.reshape(np.array(data),(-1,))
        return np_data, len(np_data)
