"""A high-resolution monotonic timer

Python 3.3+ provides the time.perf_counter() function, which is a high-resolution monotonic timer.
"""

__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''

from time import perf_counter, sleep


def get_time():
    """Get high-resolution time stamp (float) """
    return perf_counter()


class Timer(object):#
    """A simple timer"""

    def __init__(self, sync_timer=None):
        if sync_timer is None:
            self._init_time = get_time()
        else:
            self._init_time = sync_timer._init_time

    @property
    def time(self):
        return int((get_time() - self._init_time) * 1000)

    def wait(self, waiting_time, function=None):
        """Wait for a certain amount of milliseconds.
        """

        start = self.time
        looptime = 200
        if waiting_time > looptime:
            sleep((waiting_time - looptime) / 1000)
        while self.time < start + waiting_time:
            pass

def get_time_ms():
    return int(1000*get_time())

app_timer = Timer()