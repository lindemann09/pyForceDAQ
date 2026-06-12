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
        self, recording_settings: RecordingSettings,
        filepath: Path|str = "",
        append_mode: bool = False,
        float_decimal_places: int = 4
    ):
        """To write to a file from multiple processes. Use FileWriter.queue.put(str) to write file"""

        super().__init__()
        self._filepath: Path  = Path(filepath)
        self._append_mode = append_mode
        self.queue = Queue()
        self._force_quit = Event()
        self._close_file = Event()
        self._write_forces = recording_settings.array_write_forces()
        self._write_trigger = recording_settings.array_write_trigger()
        self._write_deviceid = len(recording_settings.device_labels) > 1
        self._decimal_places = float_decimal_places

    @property
    def filepath(self) -> Path:
        return self._filepath

    def set_file(self, file_path: Path|str, append_mode: bool = False):
        """Set file path and append mode for the file writer."""
        self._filepath = Path(file_path)
        self._append_mode = append_mode

    def close_file(self):
        """closes file after all pending writes are done and no further write occurred
        for close_timeout seconds
        """
        self._close_file.set()

    def force_quit(self):
        """forces the process to quit immediately, even if there are pending writes in the queue"""
        self._force_quit.set()

    def join(self, timeout=None):
        self._close_file.set()
        super().join(timeout)

    def run(self):

        if self._filepath is None:
            raise ValueError("File path is not set. Call set_file() with a valid file path before running the process.")

        float_format = "{0:." + str(self._decimal_places) + "f},"
        if self._append_mode:
            mode = "a"
        else:
            mode = "w"
        if self._filepath.suffix.endswith("bz2"):
            fl = bz2.open(self._filepath, mode)
        else:
            fl = open(self._filepath, mode, encoding=ENCODING)

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

