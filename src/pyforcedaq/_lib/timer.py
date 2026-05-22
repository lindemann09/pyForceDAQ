"""A high-resolution monotonic timer

Python 3.3+ provides the time.perf_counter() function, which is a high-resolution monotonic timer.
"""

__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''

from time import perf_counter, sleep


def get_time_ms() -> int:
    """Get high-resolution time stamp (int) """
    return int(1000 * perf_counter())

class Timer(object):#
    """A simple clock class that can be used to measure elapsed time in milliseconds."""

    def __init__(self, sync_timer=None):
        if sync_timer is None:
            self._init_time = get_time_ms()
        else:
            self._init_time = sync_timer._init_time

    @property
    def time(self):
        return get_time_ms() - self._init_time


def wait(waiting_time):
    """Wait for a certain amount of milliseconds.
    """

    start = get_time_ms()
    looptime = 200
    if waiting_time > looptime:
        sleep((waiting_time - looptime) / 1000)
    while get_time_ms() < start + waiting_time:
        pass


app_clock = Timer()