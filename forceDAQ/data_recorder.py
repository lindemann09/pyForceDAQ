"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import os
import atexit
from time import localtime, strftime,asctime
import gzip

from forceDAQ_types import ForceData, UDPData, DAQEvents, CODE_SOFTTRIGGER, CODE_UDPDATA
from forceDAQ_types import GUIRemoteControlCommands as RemoteCmd
from udp_connection import UDPConnectionProcess
from daq import SensorSettings, SensorProcess
from forceDAQ import __version__ as forceDAQVersion


class DataRecorder(object):
    """handles multiple sensors and udp connection"""

    def __init__(self, force_sensor_settings, timer,
                 poll_udp_connection=False):


        """queue_data will be saved
        see sensorprocess.__init__
        """

        self.timer = timer
        #create sensor processes
        if not isinstance(force_sensor_settings, list):
            force_sensor_settings = [force_sensor_settings]
        self._force_sensor_processes =[]

        self.sample_counter = {}
        for fs in force_sensor_settings:
            if not isinstance(fs, SensorSettings):
                RuntimeError("Recorder needs a list of Force Sensor Settings!")
            else:
                fst = SensorProcess(settings = fs,
                                    pipe_buffered_data_after_pause=True)
                fst.start()
                self._force_sensor_processes.append(fst)
                self.sample_counter[fs.device_id] = 0

        # create udp connection process
        if poll_udp_connection:
            self.udp = UDPConnectionProcess(sync_timer=self.timer)
            self.udp.start()
        else:
            self.udp = None

        self._is_recording = False
        self._file = None
        self._soft_trigger = []
        atexit.register(self.quit)


    def force_sensor_process(self, sensor_id):
        if 0 <= sensor_id < len(self._force_sensor_processes):
            return self._force_sensor_processes[sensor_id]

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

        buffer = self.pause_recording()
        self.close_data_file()

        if self.udp is not None:
            self.udp.stop()

        # wait that all processes are quitted
        for fsp in self._force_sensor_processes:
            fsp.stop()

        return buffer

    def process_udp_events(self):
        """process udp events and return them"""
        buffer = []
        while True:
            try:
                data = self.udp.receive_queue.get_nowait()
            except:
                # until queue empty or no udp connection
                break
            buffer.append(data)
        self._write_data(buffer)
        return buffer

    def _write_data(self, data_buffer):
        """ writes data to disk and set counters

        ignore UDP remote control commands
        """

        for d in data_buffer:
            if isinstance(d, ForceData):
                self.sample_counter[d.device_id] += 1

            if self._file is not None:
                if isinstance(d, ForceData):
                    self._file.write("%d,%d,%.4f,%.4f,%.4f\n" % \
                                 (d.device_id, d.time,
                                  d.Fx, d.Fy, d.Fz)) # write ascii data to file todo does not write trigger or torque
                elif isinstance(d, DAQEvents):
                     self._file.write("%d,%d,%s,0,0\n" % \
                                 (CODE_SOFTTRIGGER, d.time, str(d.code))) # write ascii data to fill todo: DOC output format
                elif isinstance(d, UDPData):
                    if not d.string.startswith(RemoteCmd.COMMAND_STR):
                        self._file.write("%d,%d,%s,0,0\n" % \
                                     (CODE_UDPDATA, d.time, d.string)) # write ascii data to fill


    def write_soft_trigger(self, code, time=None):
        """Set marker code in file

        Trigger will be timestamps and occur in the data output

        """
        if time is None:
            time = self.timer.time
        self._soft_trigger.append(DAQEvents(time = time, code = code))


    def start_recording(self, determine_bias=False):
        """Start polling process and record

        See Also
        --------
        is_recording

        """

        if determine_bias:
            self.determine_biases(n_samples=1000)

        if sum(map(lambda x:not(x.event_bias_is_available.is_set()),
                    self._force_sensor_processes)):
            raise RuntimeError("Sensors can't be started before bias has been determined.")

        # start polling
        map(lambda x:x.start_polling(), self._force_sensor_processes)
        self._is_recording = True

    def pause_recording(self):
        """Pauses all polling processes and process data

        returns
        --------
        data : all last data

        """
        self._is_recording = False

        data = []
        #sensors
        for fsp in self._force_sensor_processes:
            buffer = fsp.pause_polling_get_buffer()
            self._write_data(buffer)
            data.extend(buffer)

        # udp event
        buffer = self.process_udp_events()
        data.extend(buffer)
        # soft trigger
        self._write_data(self._soft_trigger)
        data.extend(self._soft_trigger)
        self._soft_trigger = []

        return data

    def determine_biases(self, n_samples):
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
        map(lambda x:x.determine_bias(n_samples=n_samples),
            self._force_sensor_processes)
        map(lambda x:x.event_bias_is_available.wait(), self._force_sensor_processes)

    def open_data_file(self, filename, directory="data",
                       time_stamp_filename=False,
                       varnames = True,
                       comment_line="",
                       zipped=False):
        """Create a data file

        Only if data file has been opened, data will be saved!

        Parameters
        ----------
        filename : string
            the filename
        directory : string, optional
            the data subdirectory
        time_stamp_filename : boolean, optional
            if True all filename will contain a timestamp. This is usefull to
            ensure that data will not overwritten
        varnames : boolean, optional
            write variable names in first line of data output
        comment_line : string, optional
            add some comments at the beginning of the data output file
        zippers : boolean, optional
            are the data zipped or not. Note: Saving zipped data after pause
            takes much longer.

        Returns
        -------
        filename : string
                the actually used filename (incl. timestamp)

        """

        if not os.path.isdir(directory):
            os.mkdir(directory)
        self.close_data_file()

        if filename is None or len(filename) == 0:
            filename = "daq_recording.csv"

        if zipped:
            suffix = ".gz"
        else:
            suffix = ""

        cnt = 0
        while True:
            flname = filename
            if cnt>0:
                x = flname.find(".")
                if x<0:
                    x = len(flname)
                flname = flname[:x] + "_{0}".format(cnt) + flname[x:]

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

        if zipped:
            self._file = gzip.open(directory + os.path.sep + self.filename, 'w+')
        else:
            self._file = open(directory + os.path.sep + self.filename, 'w+')
        print "Data file: ", self.filename

        self._file.write("# Recorded at {0} with pyForceDAQ {1}\n".format(
            asctime(localtime()), forceDAQVersion))

        if len(comment_line)>0:
            self._file.write("#" + comment_line + "\n")
        if varnames:
            self._file.write("device_tag, time, Fx, Fy, Fz\n")
        return self.filename

    def close_data_file(self):
        """Close the data file

        Afterwards data will not be saved anymore.

        """

        if self._file is not None:
            self._file.close()
            self._file = None