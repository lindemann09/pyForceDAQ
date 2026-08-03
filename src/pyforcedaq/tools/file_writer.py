import bz2
from abc import ABC, abstractmethod
from multiprocessing import Event, Process, Queue
from pathlib import Path
from queue import Empty

NEWLINE = "\n"
ENCODING = "utf-8"

class AbstractCSVDataStruct(ABC):
    ...

class AbstractFileWriter(ABC, Process):
    """FileWriter is a process that runs in the background and writes data to a file.
    You can send data to be written by putting it into the queue attribute of the FileWriter instance.
    You need to start the process by calling the start() method. The process will run until you call
    the join() method or the program exits.

    Instructions to use  the FileWriter process:
    1. The data structure you want to save with FileWriter as csv has to be a subclass of
        AbstractCSVDataStruct.
    2. Create a subclass of AbstractFileWriter and implement the to_csv method to convert your
        data structure to a CSV string.

    """
    def __init__(
        self,
        filepath: Path|str,
        append_mode: bool = False,
    ):
        """To write to a file from multiple processes. Use FileWriter.queue.put(str) to write file"""

        super().__init__()
        self._filepath: Path  = Path(filepath)
        self._append_mode = append_mode
        self.queue = Queue()
        self._enforce_quit = Event()
        self._close_file = Event()

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

    def enforce_quit(self):
        """forces the process to quit immediately, even if there are pending writes in the queue"""
        self._enforce_quit.set()

    def join(self, timeout=None):
        self._close_file.set()
        super().join(timeout)

    @abstractmethod
    def to_csv(self, data: AbstractCSVDataStruct) -> str:
        ...

    def run(self):

        if self._filepath is None:
            raise ValueError("File path is not set. Call set_file() with a valid file path before running the process.")
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

        print(f"FileWriter: writing to {self._filepath} (append_mode={self._append_mode})")
        if self._append_mode:
            mode = "a"
        else:
            mode = "w"
        if self._filepath.suffix.endswith(".bz2"):
            fl = bz2.open(self._filepath, mode)
        else:
            fl = open(self._filepath, mode, encoding=ENCODING)

        self._close_file.clear()
        self._enforce_quit.clear()

        while not self._enforce_quit.is_set():

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

            if isinstance(d, AbstractCSVDataStruct):
                txt = self.to_csv(d) + NEWLINE

            elif isinstance(d, str):
                txt = f"{d}"
            else:
                continue  # ignore unknown

            if isinstance(fl, bz2.BZ2File):
                fl.write(txt.encode(ENCODING))
            else:
                fl.write(txt)

        fl.flush()
        fl.close()


def unique_file_path(path: Path|str) -> Path:
    """Generates a unique file path by appending a number to the base path if the file already exists."""
    path = Path(path)
    stem_parts = path.stem.rsplit("_", 1)
    stem = stem_parts[0]
    try:
        counter = int(stem_parts[-1])
    except ValueError:
        counter = 1
        stem = path.stem


    unique_path = path
    while True:
        if not unique_path.exists():
            return unique_path
        unique_path = path.with_name(f"{stem}_{counter}{path.suffix}")
        counter += 1
