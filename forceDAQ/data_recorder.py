"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""
__author__ = "Oliver Lindemann"


import os
import atexit
from multiprocessing import Queue
from time import localtime, strftime, sleep
from clock import Clock
import force_sensor
from udp_connection import UDPData, UDPConnectionProcess

class SoftTrigger(object):
    """The SoftTrigger data class, used to store trigger

    See Also
    --------
    DataRecorder.set_soft_trigger()

    """

    def __init__(self, time, code):
        """Create a SoftTrigger object

        Parameters
        ----------
        time : int
        code: numerical or string

        """
        self.time = time
        self.code = code


class DataRecorder(object):
    """handles multiple sensors and udp connection"""

    def __init__(self, force_sensors, poll_udp_connection=False,
                    max_buffer_size=10000, sync_clock=None):


        """Array of ForceSensors

        Starts processes
        create sensor processes and write data the file"""

        self._queue = Queue()
        self.clock = Clock(sync_clock)

        #create sensor processes
        if not isinstance(force_sensors, list):
            force_sensors = [force_sensors]
        self._force_sensor_processes =[]

        self.sample_counter = {}
        for fs in force_sensors:
            if not isinstance(fs, force_sensor.Settings):
                RuntimeError("Recorder needs a list of ForceSensors!")
            else:
                fst = force_sensor.SensorProcess(settings= fs,
                                                 data_queue = self._queue)
                fst.start()
                self._force_sensor_processes.append(fst)
                self.sample_counter[fs.device_id] = 0

        # create udp connection process
        if poll_udp_connection:
            self.udp = UDPConnectionProcess(self._queue, sync_clock=self.clock)
            self.udp.start()
            self.udp.event_polling.wait()
            self.udp.event_polling.clear() # stop polling directly
        else:
            self.udp = None

        self._is_recording = False
        self._file = None
        self._data_buffer = []
        self.max_buffer_size = max_buffer_size
        self.pause_recording()
        atexit.register(self.quit)


    @property
    def is_recording(self):
        """Property indicates whether the recording is started or paused"""
        return self._is_recording

    def quit(self):
        """Stop all recording processes, close data file and quit recording

        Notes
        -----
        Will be automatically called at exit.

        """

        map(lambda x:x.stop(), self._force_sensor_processes)

        if self.udp is not None:
            self.udp.stop()

        # process all data until all processes are dead (finish putting processes)
        while True:
            sleep(0.1)
            self.process_sensor_input()
            if sum(map(lambda x:x.is_alive(), self._force_sensor_processes)) == 0:
                break

        self.close_data_file()


    def process_sensor_input(self):
        """Reads data from process queue and writes data to disk

        Notes
        -----
        This function should be called frequently. The execution of the function
        might take a while, if the last call was performed a while ago.

        """

        while True:
            try:
                data = self._queue.get_nowait()
            except:
                # until queue empty
                return

            if isinstance(data, force_sensor.ForceData):
                self.sample_counter[data.device_id] += 1

            if self._file is not None:
                if isinstance(data, force_sensor.ForceData):
                    self._file.write("%d,%d,%d, %.4f,%.4f,%.4f\n" % \
                                 (data.device_id, data.time, data.counter,
                                  data.Fx, data.Fy, data.Fz)) # write ascii data to file todo does not write trigger or torque
                elif isinstance(data, SoftTrigger):
                     self._file.write("#T,%d,%d,0,0,0\n" % \
                                 (data.time, data.code)) # write ascii data to fill todo: DOC output format

                if isinstance(data, UDPData):
                     self._file.write("#UDP,%d,%s,0,0,0\n" % \
                                 (data.time, data.string)) # write ascii data to fill todo: DOC output format

            # add data to buffer
            self._data_buffer.append(data)
            while (len(self._data_buffer) > self.max_buffer_size):
                self._data_buffer.pop(0)

    def set_soft_trigger(self, code):
        """Set a software trigger

        Trigger will be timestamps and occur in the data output

        """
        self._queue.put_nowait(SoftTrigger(time = self.clock.time, code = code))

    def get_buffer(self):
        """Gets the all data in the FIFO buffer and clears the buffer. The most
        recent sample is thus get_buffer()[-1].

        Returns
        --------
        data_array : array of data (ForceData, SoftTrigger or UDPData)

        Notes
        -----
        The function calls process_sensor_input and might therefore take some
        time, if the last process_data was not called recently

        Check buffer size to control whether data might have been missed data,
        since your last get_last_data call. This might be the case if
        `len(data_recorder.get_last_data()) >= data_recorder.max_buffer_size`.
        """

        self.process_sensor_input()
        rtn = self._data_buffer
        self._data_buffer = []
        return rtn

    @property
    def buffer_size(self):
        """Getter for the current size of the FIFO buffer

        Notes
        -----
        The function calls process_sensor_input and might therefore take some
        time, if the last process_data was not called recently

        """

        self.process_sensor_input()
        return len(self._data_buffer)

    def start_recording(self):
        """Start polling process and record

        See Also
        --------
        is_recording

        """

        # start processes
        map(lambda x:x.event_polling.set(), self._force_sensor_processes)
        if self.udp is not None:
            self.udp.event_polling.set() # start polling
        self._is_recording = True

    def pause_recording(self):
        """Pauses all polling processes and pause recording
        """

        map(lambda x:x.event_polling.clear(), self._force_sensor_processes)
        if self.udp is not None:
            self.udp.event_polling.clear()
        self._is_recording = False
        self.process_sensor_input()

    def determine_biases(self, n_samples=100):
        """Record n data samples (n_samples) to determine bias.
        Afterwards recording is in pause mode

        Notes
        -----
        The function take some time to be processed

        See Also
        --------
        Sensor.determine_bias()

        """

        self.pause_recording()
        self.process_sensor_input()
        map(lambda x:x.determine_bias(n_samples=n_samples),
            self._force_sensor_processes)
        map(lambda x:x.event_bias_is_available.wait(), self._force_sensor_processes)

    def open_data_file(self, filename, directory="data", suffix=".csv",
                       time_stamp_filename=False,
                       varnames = True,
                       comment_line=""):
        """Create a data file

        Only if data file has been opened, data will be saved!

        Parameters
        ----------
        filename: string
            the filename
        directory: string, optional
            the data subdirectory
        suffix: string, optional
            the data filename suffix
        time_stamp_filename: boolean, optional
            if True all filename will contain a timestamp. This is usefull to
            ensure that data will not overwritten
        varnames: boolean, optional
            write variable names in first line of data output
        comment_line: string, optional
            add some comments at the beginning of the data output file

        Returns
        -------
        filename: string
                the actually used filename (incl. timestamp)

        """

        if not os.path.isdir(directory):
            os.mkdir(directory)
        self.close_data_file()

        if filename is None or len(filename) == 0:
            filename = "daq_recording"
        cnt = 0
        while True:
            flname = filename
            if cnt>0:
                flname += "_{0}".format(cnt)
            if time_stamp_filename:
                self.filename = flname + "_" + \
                        strftime("%Y%m%d%H%M", localtime()) + suffix
            else:
                self.filename = flname + suffix

            if os.path.isfile(directory + os.path.sep + self.filename):
                # print "data file already exists, adding counter"
                cnt += 1
            else:
                break

        self._file = open(directory + os.path.sep + self.filename, 'w+')
        print "Data file: ", self.filename
        if len(comment_line)>0:
            self._file.write("#" + comment_line + "\n")
        if varnames:
            self._file.write("#device_tag, time, counter, Fx, Fy, Fz")
        return self.filename

    def close_data_file(self):
        """Close the data file

        Afterwards data will not be saved anymore.

        """

        if self._file is not None:
            self._file.close()
            self._file = None

