
from multiprocessing import Event, Process, Queue
from pathlib import Path
from queue import Empty


class FileWriter(Process):

    def __init__(self, filepath:str | Path, append_file:bool=False, close_timeout:float=0.1, autostart:bool=True):
        """To write to a file from multiple processes. Use FileWriter.queue.put(str) to write file
        """

        super().__init__()
        self.filepath = Path(filepath)
        self.append_mode = append_file
        self.close_timeout = close_timeout
        self.queue = Queue()
        self._force_quit = Event()
        self._close_file = Event()
        self._close_file.clear()
        self._force_quit.clear()
        if autostart:
            self.start()

    def close_file(self):
        """closes file after all pending writes are done and no further write occurred
        for close_timeout seconds
        """
        self._close_file.set()

    def force_quit(self):
        """forces the process to quit immediately, even if there are pending writes in the queue"""
        self._force_quit.set()

    #def join(self, timeout=None):
    #    super(FileWriter, self).join(timeout)

    def run(self):
        if self.append_mode:
            mode = 'a'
        else:
            mode = 'w'
        with open(self.filepath, mode, encoding='utf-8') as fl:
            while not self._force_quit.is_set():
                try:
                    line = self.queue.get(timeout=self.close_timeout)
                except Empty:
                    if self._close_file.is_set():
                        break
                    else:
                        continue
                fl.write(line)

            fl.flush()

