import numpy as np

from .clock import local_clock


class PollingTimeProfile(object):

    def __init__(self, timing_range_ms=10):
        self._last = None
        self._timing_range_ms = 10
        self._zero_cnt = 0

        #self._zero_time_polling_frequency = {}
        self.profile_frequency = np.array([0] * (timing_range_ms + 1))

    def stop(self):
        self._last = None

    def update(self, time: float):

        time_ms = int(time * 1000)
        if self._last is not None:
            d = time_ms - self._last
            if d > self._timing_range_ms:
                d = self._timing_range_ms
            self.profile_frequency[d] += 1

            #if d == 0:
            #    self._zero_cnt += 1
            #elif self._zero_cnt > 0:
            #    try:
            #        self._zero_time_polling_frequency[self._zero_cnt] += 1
            #    except:
            #        self._zero_time_polling_frequency[self._zero_cnt] = 1
            #    self._zero_cnt = 0

        self._last = time_ms

    def tick(self):
        self.update(local_clock())

    @property
    def profile_percent(self):
        n = np.sum(self.profile_frequency)
        return self.profile_frequency / n

    def get_profile_str(self):
        rtn = str(list(self.profile_frequency)
                  ).replace("[", "").replace("]", "").replace(" ", "")
        return "polling profile [{}]".format(rtn)

    #@property
    #def zero_time_polling_frequency(self):
    #    return np.array(list(self._zero_time_polling_frequency.items()))