"""class to record force sensor data

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import atexit
import logging
from pathlib import Path
from time import asctime, localtime, strftime
from typing import List

from .. import __version__ as forceDAQVersion
from .. import constants
from .file_writer import FileWriter
from .misc import set_logging
from .process_priority_manager import ProcessPriorityManager
from .sensor_process import SensorProcess
from .settings import RecordingSettings, SensorSettings
from .types import DAQEvents, ForceSensorData, PollingPriority
from .udp_connection import UDPConnectionProcess

set_logging(data_directory="data", log_file="recording.log")

# FIXME LSL marker event for all events


class DataRecorder(object):
    """handles multiple sensors and udp connection"""

    def __init__(
        self,
        recording_settings: RecordingSettings,
        force_sensor_settings: SensorSettings | List[SensorSettings],
        poll_udp_connection: bool = False,
    ):
        """queue_data will be saved
        see sensorprocess.__init__

        polling_priority has to be types.PollingPriority.{HIGH},
        {REALTIME} or {NORMAL} or None

        You can change the used modules by settings the following constants before creating the
        DataRecorder instance:
            * set constants.DAQ_TYPE to constants.PYDAQMX, constants.NIDAQMX or constants.MOCK_SENSOR
            * set constants.USE_AIFTT to True or False
        """

        if not isinstance(force_sensor_settings, list):
            force_sensor_settings = [force_sensor_settings]

        self.recording_settings = recording_settings
        self.file_writer = FileWriter(recording_settings)

        # create sensor processes
        self.force_sensor_processes: List[SensorProcess] = []
        event_trigger = []
        for fs in force_sensor_settings:
            if not isinstance(fs, SensorSettings):
                raise RuntimeError("Recorder needs a list of Force Sensor Settings!")
            else:
                fst = SensorProcess(
                    sensor_settings=fs,
                    recording_settings=recording_settings,
                    file_writer_queue=self.file_writer.queue,
                    daq_type=constants.DAQ_TYPE,
                    use_aiftt=constants.USE_AIFTT)
                fst.start()
                event_trigger.append(fst.event_trigger)
                self.force_sensor_processes.append(fst)

        # create udp connection process
        if poll_udp_connection:
            self.udp = UDPConnectionProcess(event_trigger=event_trigger)
            self.udp.start()
        else:
            self.udp = None

        # process managing FIYME needed?
        self._proc_manager = ProcessPriorityManager()
        self._proc_manager.add_subprocess(self.udp)
        self._proc_manager.add_subprocess(self.force_sensor_processes)
        if self.recording_settings.priority is not None:
            level = PollingPriority.NORMAL
        else:
            level = PollingPriority.get_priority(self.recording_settings.priority)
        self._proc_manager.set_subprocess_priorities(level=level, disable_gc=False)

        logging.info(
            "Main process priority: %s", self._proc_manager.get_main_priority()
        )
        # logging.info("Subprocess priorities: {}".format(self._proc_manager.get_subprocess_priorities()))

        self._is_saving = False
        self._daq_event = [] # FIXME needed?
        atexit.register(self.quit)

    @property
    def has_file_writer(self):
        """Property indicates whether a data file is open"""
        return self.file_writer is not None

    @property
    def is_alive(self):
        """Property indicates whether the recording processes are alive"""
        try:
            return self.force_sensor_processes[0].is_alive()
        except Exception:
            return False

    @property
    def is_saving(self):
        """Property indicates whether the recording is started or paused"""
        return self._is_saving

    @property
    def sensor_settings_list(self):
        return list(map(lambda x: x.sensor_settings, self.force_sensor_processes))

    def quit(self) -> list | None:
        """Stop all recording processes, close data file and quit recording

        Notes
        -----
        Will be automatically called at exit.

        """

        if not self.is_alive:
            return

        self.pause_saving()
        for fsp in self.force_sensor_processes:
            fsp.join()
        self.close_data_file()

        if self.udp is not None:
            self.udp.quit()

        logging.info("Quit recording")

    def process_and_write_udp_events(self) -> list:
        """process udp events and return them"""
        buffer = []
        while True:
            try:
                data = self.udp.receive_queue.get_nowait()  # type: ignore
            except AttributeError:
                # until queue empty or no udp connection
                break
            buffer.append(data)

        for dat in buffer:
            self.file_writer.queue.put(dat)
        return buffer

    def store_daq_event(
        self, code: str | int | float, time: float | None = None
    ) -> None:
        """Set marker code in file

        DAQEvent will be timestamps and occur in the data output

        """
        self._daq_event.append(DAQEvents(time=time, code=code))

    def start_saving(self) -> None:
        """Start polling process and record

        See Also
        --------
        is_saving

        """

        for fsp in self.force_sensor_processes:
            fsp.flag_sensor_bias_is_determined.wait() # wait is no initial bias is set yet
            fsp.start_saving()
        self._is_saving = True

    def pause_saving(self):
        """Pauses all polling processes and process data

        returns
        --------
        data : all last data

        """

        # pause polling
        for fsp in self.force_sensor_processes:
            fsp.pause_saving()
        self._is_saving = False # FEEDBACK RECORDER SCREEN


    def determine_biases(self) -> None:
        for x in self.force_sensor_processes:
            x.determine_bias()

    def open_data_file(
        self,
        filename: str | Path,
        subdirectory: str = "data",
        varnames: bool = True,
        comment_line: str = "",
    ) -> Path:
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

        Returns
        -------
        filename : string
                full path the actually used file (incl. timestamp)

        """

        # create filename
        data_dir = Path.cwd() / subdirectory
        data_dir.mkdir(exist_ok=True)

        if self.recording_settings.zip_data:
            filename = Path(filename).with_suffix(".csv.gz")
        else:
            filename = Path(filename).with_suffix(".csv")
        while True:
            file_path = data_dir / filename
            if file_path.is_file():
                #get unique filename by adding timestamp if file already exists
                filename = Path(
                    filename.stem
                    + "_"
                    + strftime("%m%d%H%M", localtime())
                    + filename.suffix
                )
            else:
                break

        self.file_writer.start_recording(file_path=file_path, append_mode=False)
        logging.info("new file: %s", file_path)

        self.file_writer.queue.put(
            f"Recorded at {asctime(localtime())} with pyForceDAQ {forceDAQVersion}\n")

        for s in self.sensor_settings_list:
            txt = f" Sensor: label={s.device_label}, cal-file={s.calibration_file}\n"
            self.file_writer.queue.put(txt)

        if len(comment_line) > 0:
            self.file_writer.queue.put(comment_line + "\n")

        if varnames:
            write_forces = self.recording_settings.array_write_forces()
            write_trigger = self.recording_settings.array_write_trigger()
            write_deviceid = len(self.recording_settings.device_labels) > 1
            line = "time,"
            if write_deviceid:
                line += "device_tag,"
            for x in range(6):
                if write_forces[x]:
                    line += ForceSensorData.forces_names[x] + ","
            if write_trigger[0]:
                line += "trigger1,"
            if write_trigger[1]:
                line += "trigger2,"
            self.file_writer.queue.put(line[:-1] + "\n")

        return file_path

    def close_data_file(self) -> None:
        """Close the data file

        Afterwards data will not be saved anymore.

        """
        self.file_writer.close_file()
        if self.file_writer.is_alive():
            self.file_writer.join()
        self.file_writer.filepath = Path("")
