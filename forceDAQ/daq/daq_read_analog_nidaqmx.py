import ctypes as ct
import numpy as np
import nidaqmx

from ._config import NUM_SAMPS_PER_CHAN, TIMEOUT, NI_DAQ_BUFFER_SIZE\

class DAQReadAnalog(nidaqmx.Task):

    NUM_SAMPS_PER_CHAN = NUM_SAMPS_PER_CHAN
    TIMEOUT = TIMEOUT
    NI_DAQ_BUFFER_SIZE = NI_DAQ_BUFFER_SIZE

    def __init__(self, configuration, read_array_size_in_samples):
        """ TODO
        read_array_size_in_samples for ReadAnalogF64 call

        """
        
        #print('init')
        nidaqmx.Task.__init__(self)
        # CreateAIVoltageChan
        self.ai_channels.add_ai_voltage_chan(configuration.physicalChannel, # physicalChannel
                            "",                         # nameToAssignToChannel,
                            nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL,     # terminalConfig
                            configuration.minVal, configuration.maxVal,  # min max Val
                            nidaqmx.constants.VoltageUnits.VOLTS,    # units
                            None                        # customScaleName
                            )
        print('added channels')
        #CfgSampClkTiming
        self.timing.cfg_samp_clk_timing(configuration.rate,          # rate
                            "",                 # source
                            nidaqmx.constants.Edge.RISING,   # activeEdge
                            nidaqmx.constants.AcquisitionType.CONTINUOUS,# sampleMode
                            ct.c_uint64(DAQReadAnalog.NI_DAQ_BUFFER_SIZE) # sampsPerChanToAcquire, i.e. buffer size
                            )
        print('devices')
        print(nidaqmx.Task.devices)
        self.device_id = configuration.device_id
        self._task_is_started = False
        self.read_array_size_in_samples = ct.c_uint32(read_array_size_in_samples)
        #print(self.read_array_size_in_samples )

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
        data = self.read(DAQReadAnalog.NUM_SAMPS_PER_CHAN.value,
                                DAQReadAnalog.TIMEOUT.value)
        np_data = np.reshape(np.array(data),(-1,))
        return np_data, DAQReadAnalog.NUM_SAMPS_PER_CHAN.value
