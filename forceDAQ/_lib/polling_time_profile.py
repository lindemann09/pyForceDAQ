from .timer import get_time
import numpy as np

class PollingTimeProfile(object):

    def __init__(self, timing_range=10):
        self._last = None
        self._timing_range = 10
        self._zero_cnt = 0

        self._zero_time_polling_frequency = {}
        self.profile_frequency = np.array([0] * (timing_range + 1))

    def stop(self):
        self._last = None

    def update(self, time_ms):
        if self._last is not None:
            d = time_ms - self._last
            if d > self._timing_range:
                d = self._timing_range
            self.profile_frequency[d] += 1

            if d == 0:
                self._zero_cnt += 1
            elif self._zero_cnt > 0:
                try:
                    self._zero_time_polling_frequency[self._zero_cnt] += 1
                except:
                    self._zero_time_polling_frequency[self._zero_cnt] = 1
                self._zero_cnt = 0

        self._last = time_ms

    def tick(self):
        self.update(int(1000*get_time()))

    @property
    def profile_percent(self):
        n = np.sum(self.profile_frequency)
        return self.profile_frequency / n

    @property
    def zero_time_polling_frequency(self):
        return np.array(list(self._zero_time_polling_frequency.items()))