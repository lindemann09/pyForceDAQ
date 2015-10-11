"""Sensor History with moving average filtering and distance, velocity"""

import math

class Thresholds(object):

    def __init__(self, thresholds):
        """Thresholds for a particular sensor"""
        self._thresholds = list(thresholds)
        self._thresholds.sort()
        self._prev_level = None

    def get_level(self, value):
        """return [int, boolean]
        int: the level of current sensor value depending of thresholds (array)
        boolean is true if sensor level has been changed since last call

        return:
                0 below smallest threshold
                1 large first but small second threshold
                ..
                x larger highest threshold (x=n thresholds)
        """

        level = None
        for cnt, x in enumerate(self._thresholds):
            if value < x:
                level = cnt
                break
        if level is None:
            level = cnt + 1
        changed = (level != self._prev_level)
        if changed:
            self._prev_level = level
        return (level, changed)




class SensorHistory(object):
    """The Sensory History keeps track of the last n recorded sample and
    calculates online the moving average (running mean).

    SensorHistory.moving_average

    """

    def __init__(self, history_size, number_of_parameter):
        self.history = [[0] * number_of_parameter] * history_size
        self.moving_average = [0] * number_of_parameter
        self._correction_cnt = 0
        self._previous_moving_average = self.moving_average

    def __str__(self):
        return str(self.history)

    def update(self, values):
        """Update history and calculate moving average

        (correct for accumulated rounding errors ever 10000 samples)

        Parameter
        ---------
        values : list of values for all sensor parameters

        """

        self._previous_moving_average = self.moving_average
        pop = self.history.pop(0)
        self.history.append(values)
        # pop first element and calc moving average
        if self._correction_cnt > 10000:
            self._correction_cnt = 0
            self.moving_average = self.calc_history_average()
        else:
            self._correction_cnt += 1
            self.moving_average = map(
                lambda x: x[0] + (float(x[1] - x[2]) / len(self.history)),
                zip(self.moving_average, values, pop))


    def calc_history_average(self):
        """Calculate history averages for all sensor parameter.

        The method is more time consuming than calling the property
        `moving_average`. It is does however not suffer from accumulated
        rounding-errors such as moving average.

        """

        s = [float(0)] * self.number_of_parameter
        for t in self.history:
            s = map(lambda x: x[0] + x[1], zip(s, t))
        return map(lambda x: x / len(self.history), s)


    @property
    def history_size(self):
        return len(self.history)

    @property
    def number_of_parameter(self):
        return len(self.history[0])

    @property
    def previous_moving_average(self):
        return self._previous_moving_average


if __name__ == "__main__":
    import random
    def run():
        sh = SensorHistory(history_size=5, number_of_parameter=3)
        thr = Thresholds([35, 20, 50, 80, 90])
        for x in range(1998):
            x = [random.randint(0, 10), random.randint(0, 100),
                    random.randint(0, 100)]
            sh.update(x)

        print sh.moving_average, sh.calc_history_average()
        print thr._thresholds
        print thr.get_level(80)

    import timeit
    print timeit.timeit(run, number=1)
