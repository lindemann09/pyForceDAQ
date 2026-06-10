import bz2
from multiprocessing import Event, Process, Queue
from pathlib import Path
from queue import Empty

from .settings import RecordingSettings
from .types import TAG_COMMENTS, ForceSensorData

NEWLINE = "\n"
ENCODING = "utf-8"

class FileWriter(Process):
    def __init__(
        self, recording_settings: RecordingSettings, float_decimal_places: int = 4
    ):
        """To write to a file from multiple processes. Use FileWriter.queue.put(str) to write file"""

        super().__init__()
        self.filepath: Path  = Path("")
        self.append_mode = False
        self.queue = Queue()
        self._force_quit = Event()
        self._close_file = Event()
        self._write_forces = recording_settings.array_write_forces()
        self._write_trigger = recording_settings.array_write_trigger()
        self._write_deviceid = len(recording_settings.device_labels) > 1
        self._decimal_places = float_decimal_places

    def close_file(self):
        """closes file after all pending writes are done and no further write occurred
        for close_timeout seconds
        """
        self._close_file.set()

    def force_quit(self):
        """forces the process to quit immediately, even if there are pending writes in the queue"""
        self._force_quit.set()

    def start_recording(self, file_path: Path, append_mode: bool = False):
        """opens file for writing, if file already exists, it will be overwritten (or appended if append_mode is True)"""
        self.filepath = file_path
        self.append_mode = append_mode
        self.start()

    # def join(self, timeout=None):
    #    super(FileWriter, self).join(timeout)

    def run(self):

        if self.filepath is None:
            raise ValueError("File path is not set. Call start_recording() with a valid file path before running the process.")

        float_format = "{0:." + str(self._decimal_places) + "f},"
        if self.append_mode:
            mode = "a"
        else:
            mode = "w"
        if self.filepath.suffix.endswith("bz2"):
            fl = bz2.open(self.filepath, mode)
        else:
            fl = open(self.filepath, mode, encoding=ENCODING)

        self._close_file.clear()
        self._force_quit.clear()

        while not self._force_quit.is_set():

            if self._close_file.is_set():
                try:
                    d = self.queue.get_nowait()
                except Empty:
                    break  # quit process
            else:
                try:
                    d = self.queue.get(timeout=0.5)
                except Empty:
                    continue  # wait again for events

            if isinstance(d, ForceSensorData):
                txt = f"{d.time},"
                if self._write_deviceid:
                    txt += f"{d.sensor_id},"
                for x in d.forces[self._write_forces]:
                    txt += float_format.format(x)
                for x in d.trigger[self._write_trigger]:
                    if isinstance(x, int):
                        txt += f"{x},"
                    else:
                        txt += float_format.format(x)
                txt = txt[:-1] + NEWLINE

            elif isinstance(d, str):
                txt = f"{TAG_COMMENTS} {d}"
            else:
                continue  # ignore unknown data types or maybe raise error (TODO)

            if isinstance(fl, bz2.BZ2File):
                fl.write(txt.encode(ENCODING))
            else:
                fl.write(txt)

        fl.flush()
        fl.close()

