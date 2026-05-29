"""A high-resolution monotonic timer based on LSL's local_clock() function."""

from time import sleep

from pylsl import local_clock


def local_clock_ms():
    """Returns the current time in milliseconds, based on LSL's local_clock()"""
    return local_clock() * 1000


def wait_ms(waiting_time: int | float, looptime: int = 200) -> None:
    """Wait for a certain amount of milliseconds."""
    start = local_clock_ms()
    if waiting_time > looptime:
        sleep((waiting_time - looptime) / 1000)
    while local_clock_ms() < start + waiting_time:
        pass


class StopWatch(object):  #
    """A simple timer"""

    def __init__(self):
        self._init_time = local_clock()

    def reset_stopwatch(self):
        """Reset the stopwatch time to zero."""
        self._init_time = local_clock()

    @property
    def time(self) -> float:
        return local_clock() - self._init_time

    @property
    def time_ms(self) -> float:
        return self.time * 1000
