"""This module is adapted from the Expyriment 0.7.0 (www.expyriment.org)

Authors: Florian Krause <florian@expyriment.org>, Oliver Lindemann <oliver@expyriment.org>'

This file has the following licence: GNU General Public License v3

"""

__author__ = "Oliver Lindemann <oliver@expyriment.org>"

import sys
import time
import types

from timer import get_time


class Clock(object) :
    """Basic timing class.

    Unit of time is milliseconds.

    """

    if sys.platform == 'win32':
        _cpu_time = time.clock
    else:
        _cpu_time = time.time


    def __init__(self, sync_clock=None):
        """Create a clock.

        Parameters
        ----------
        sync_clock : misc.Clock, optional
            synchronise clock with existing one

        """

        if (sync_clock.__class__.__name__ == "Clock"):
            self.__init_time = sync_clock.init_time / 1000
        else:
            self.__init_time = get_time()

        self._init_localtime = time.localtime()
        self.__start = get_time()

    @property
    def init_time(self):
        """Getter for init time in milliseconds."""

        return self.__init_time * 1000

    @property
    def time(self):
        """Getter for current time in milliseconds since clock init."""

        return int((get_time() - self.__init_time) * 1000)

    @property
    def cpu_time(self):
        """Getter for CPU time."""

        return self._cpu_time()

    @property
    def stopwatch_time(self):
        """Getter for time in milliseconds since last reset_stopwatch.

        The use of the stopwatch does not affect the clock time.
        """

        return int((get_time() - self.__start) * 1000)

    @property
    def init_localtime(self):
        """Getter for init time in local time"""

        return self._init_localtime

    def reset_stopwatch(self):
        """"Reset the stopwatch.

        The use of the stopwatch does not affect the clock time.
        """

        self.__start = get_time()

    def wait(self, waiting_time, function=None):
        """Wait for a certain amout of milliseconds.

        Parameters
        ----------
        waiting_time : int
            time to wait in milliseconds
        function : function, optional
            function to repeatedly execute during waiting loop

        """

        start = self.time
        if type(function) == types.FunctionType:
            while (self.time < start + waiting_time):
                if type(function) == types.FunctionType:
                    function()
        else:
            looptime = 200
            if (waiting_time > looptime):
                time.sleep((waiting_time - looptime) / 1000)
            while (self.time < start + waiting_time):
                pass
