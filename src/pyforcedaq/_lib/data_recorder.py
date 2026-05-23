"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""
__author__ = "Oliver Lindemann"

import atexit
import gzip
import logging
from pathlib import Path
from time import asctime, localtime, strftime

from .. import __version__ as forceDAQVersion
from . import _log
from .clock import wait_ms
from .process_priority_manager import ProcessPriorityManager
from .sensor import SensorSettings
from .sensor_process import SensorProcess
from .types import (
    TAG_COMMENTS,
    TAG_DAQEVENT,
    TAG_UDPDATA,
    DAQEvents,
    ForceSensorData,
    PollingPriority,
    UDPData,
)
from .types import GUIRemoteControlCommands as RemoteCmd
from .udp_connection import UDPConnectionProcess

_log.set_logging(data_directory="data", log_file="recording.log")

NEWLINE = "\n"

class DataRecorder(object):
    """handles multiple sensors and udp connection"""

    def __init__(self, force_sensor_settings:SensorSettings | list,
                 poll_udp_connection=False,
                 write_deviceid = False,
                 polling_priority:str | None = None):


        """queue_data will be saved
        see sensorprocess.__init__

        polling_priority has to be types.PollingPriority.{HIGH},
        {REALTIME} or {NORMAL} or None
        """

        self._write_deviceid = write_deviceid

        if not isinstance(force_sensor_settings, list):
            force_sensor_settings = [force_sensor_settings]
        # write forces and triggers as define in sensor1
        self._write_forces = force_sensor_settings[0].array_write_forces()
        self._write_trigger = force_sensor_settings[0].array_write_trigger()

        # create sensor processes
        self._force_sensor_processes =[]
        event_trigger = []
        for fs in force_sensor_settings:
            if not isinstance(fs, SensorSettings):
                raise RuntimeError("Recorder needs a list of Force Sensor Settings!")
            else:
                fst = SensorProcess(settings = fs,
                                    pipe_buffered_data_after_pause=True)
                fst.start()
                event_trigger.append(fst.event_trigger)
                self._force_sensor_processes.append(fst)

        # create udp connection process
        if poll_udp_connection:
            self.udp = UDPConnectionProcess(event_trigger=event_trigger,
                                            event_ignore_tag = RemoteCmd.COMMAND_STR)
            self.udp.start()
        else:
            self.udp = None

        # process managing
        self._proc_manager = ProcessPriorityManager()
        self._proc_manager.add_subprocess(self.udp)
        self._proc_manager.add_subprocess(self._force_sensor_processes)
        if polling_priority is not None:
           level = PollingPriority.NORMAL
        else:
            level = PollingPriority.get_priority(polling_priority)
        self._proc_manager.set_subprocess_priorities(level=level, disable_gc=False)

        logging.info("Main process priority: %s", self._proc_manager.get_main_priority())
        #logging.info("Subprocess priorities: {}".format(self._proc_manager.get_subprocess_priorities()))

        self._is_recording = False
        self._file = None
        self._daq_event = []
        self.filename: str | None = None
        atexit.register(self.quit)


    @property
    def is_alive(self):
        """Property indicates whether the recording processes are alive"""
        try:
            return self._force_sensor_processes[0].is_alive()
        except Exception:
            return False

    @property
    def is_recording(self):
        """Property indicates whether the recording is started or paused"""
        return self._is_recording

    @property
    def force_sensor_processes(self):
        return self._force_sensor_processes

    @property
    def sensor_settings_list(self):
        return list(map(lambda x:x.sensor_settings,
                        self._force_sensor_processes))

    def quit(self) -> list | None:
        """Stop all recording processes, close data file and quit recording

        Notes
        -----
        Will be automatically called at exit.

        """

        if not self.is_alive:
            return

        buffer = self.pause_recording()
        self.close_data_file()

        if self.udp is not None:
            self.udp.quit()

        # wait that all processes are quitted
        for fsp in self._force_sensor_processes:
            fsp.join()

        logging.info("Quit recording")

        return buffer

    def process_and_write_udp_events(self) -> list:
        """process udp events and return them"""
        buffer = []
        while True:
            try:
                data = self.udp.receive_queue.get_nowait()
            except:
                # until queue empty or no udp connection
                break
            buffer.append(data)
        if len(buffer)>0:
            self._save_data(buffer)
        return buffer

    def _save_data(self, data_buffer: list,
                   recording_screen=None,
                   float_decimal_places: int = 4) -> None:
        """ writes data to disk and set counters

        ignores UDP remote control commands
        """
        #DOC output format

        BLOCKSIZE = 10000 # for recording screen feedback only

        float_format = "{0:." + str(float_decimal_places) + "f},"
        buffer_len = len(data_buffer)
        for c, d in enumerate(data_buffer):
            if self._file is not None:
                if isinstance(d, ForceSensorData):
                    line = f"{d.time}, {d.acquisition_delay},"
                    if self._write_deviceid:
                        line += f"{d.device_id},"
                    for x in d.selected_forces(select=self._write_forces):
                        line += float_format.format(x)
                    for x in d.selected_trigger(select=self._write_trigger):
                        if isinstance(x, int):
                            line += f"{x},"
                        else:
                            line += float_format.format(x)
                    self._file_write(line[:-1] + NEWLINE)

                elif isinstance(d, DAQEvents):
                    self._file_write(f"{TAG_DAQEVENT},{d.time},{str(d.code)}" + NEWLINE)

                elif isinstance(d, UDPData):
                    if not d.is_remote_control_command:
                        self._file_write(f"{TAG_UDPDATA},{d.time},{d.unicode}" + NEWLINE)

            if recording_screen is not None and c % BLOCKSIZE == 0:
                recording_screen.stimulus(
                    "Writing {0} of {1} blocks".format(c//BLOCKSIZE,
                                                       buffer_len//BLOCKSIZE)).present()

    def _file_write(self, s: str) -> None:
        self._file.write(s.encode())

    def save_daq_event(self, code: str | int | float, time: float | None = None) -> None:
        """Set marker code in file

        DAQEvent will be timestamps and occur in the data output

        """
        self._daq_event.append(DAQEvents(time = time, code = code))


    def start_recording(self, determine_bias: bool = False) -> None:
        """Start polling process and record

        See Also
        --------
        is_recording

        """

        if determine_bias:
            self.determine_biases(n_samples=1000)

        if len(list(filter(lambda x:x.event_bias_is_available.is_set(),
                   self._force_sensor_processes))) != len(self._force_sensor_processes):
            raise RuntimeError("Sensors can't be started before bias has been determined.")

        # start polling
        list(map(lambda x:x.start_polling(), self._force_sensor_processes))
        self._is_recording = True

    def pause_recording(self, recording_screen=None) -> list:
        """Pauses all polling processes and process data

        returns
        --------
        data : all last data

        """
        self._is_recording = False

        data = []
        if recording_screen is not None:
            recording_screen.stimulus("writing data ...").present()

        #pause polling
        for fsp in self._force_sensor_processes:
            fsp.pause_polling()

        wait_ms(500)

        # get data
        for fsp in self._force_sensor_processes:
            buffer = fsp.get_buffer()
            self._save_data(buffer, recording_screen)
            data.extend(buffer)

        # udp event
        data.extend(self.process_and_write_udp_events())

        # soft trigger
        self._save_data(self._daq_event)
        data.extend(self._daq_event)
        self._daq_event = []
        return data

    def determine_biases(self, n_samples: int) -> None:
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
        for x in self._force_sensor_processes:
            x.determine_bias(n_samples=n_samples)

        for x in self._force_sensor_processes:
            x.event_bias_is_available.wait()

    def open_data_file(self, filename: str,
                       subdirectory: str = "data",
                       time_stamp_filename: bool = False,
                       varnames: bool = True,
                       comment_line: str = "",
                       zipped: bool = False) -> Path:
        """Create a data file

        Only if data file has been opened, data will be saved!

        Parameters
        ----------
        filename : string
            the filename
        subdirectory : string, optional
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
                full path the actually used file (incl. timestamp)

        """
        data_dir = Path.cwd() / subdirectory
        data_dir.mkdir(exist_ok=True)
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

            full_path_file = data_dir / self.filename
            if full_path_file.is_file():
                # print "data file already exists, adding counter"
                cnt += 1
            else:
                break

        if zipped:
            self._file = gzip.open(full_path_file, 'w+')
        else:
            self._file = open(full_path_file, 'w+')
        print("Data file: {}".format(full_path_file))

        self._file_write(TAG_COMMENTS + "Recorded at {0} with pyForceDAQ {1}\n".format(
            asctime(localtime()), forceDAQVersion))
        logging.info("new file: {}".format(filename))

        for s in self.sensor_settings_list:
            txt = " Sensor: id={0}, name={1}, cal-file={2}\n".format(s.device_id,
                                s.sensor_name, s.calibration_file)
            self._file_write(TAG_COMMENTS + txt)

        if len(comment_line)>0:
            self._file_write(TAG_COMMENTS + comment_line + "\n")
        if varnames:
            line = "time,delay,"
            if self._write_deviceid: line += "device_tag,"
            for x in range(6):
                if self._write_forces[x]:
                    line += ForceSensorData.forces_names[x] + ","
            if self._write_trigger[0]: line += "trigger1,"
            if self._write_trigger[1]: line += "trigger2,"
            self._file_write(line[:-1] + NEWLINE)

        return full_path_file

    def close_data_file(self) -> None:
        """Close the data file

        Afterwards data will not be saved anymore.

        """

        if self._file is not None:
            self._file.close()
            self._file = None
