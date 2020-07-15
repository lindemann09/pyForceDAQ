
class Scaling(object):
    """littel helper object function to handle plotter scaling"""
    step_size = 5 # for increasing/decreasing

    def __init__(self, min, max,
                 pixel_min, pixel_max):
        """xy-value arrays"""
        self._min = min
        self._max = max
        self.pixel_min = pixel_min
        self.pixel_max = pixel_max
        self._update()

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, value):
        self._max = value
        self._update()

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, value):
        self._min = value
        self._update()

    def _update(self):
        self._zero_shift = (self._min + self._max)/2.0
        self._range = float(self._max - self._min)

    def get_pixel_factor(self):
        return (self.pixel_max - self.pixel_min) / self._range

    def increase_data_range(self):
        self.min += Scaling.step_size
        self.max -= Scaling.step_size
        if self.min >= self.max:
            self.decrease_data_range()

    def decrease_data_range(self):
        self.min -= Scaling.step_size
        self.max += Scaling.step_size

    def data_range_up(self):
         self.min += Scaling.step_size
         self.max += Scaling.step_size

    def data_range_down(self):
        self.min -= Scaling.step_size
        self.max -= Scaling.step_size

    def data2pixel(self, values):
        """ values: numeric or numpy array
        pixel_min_max: 2D array"""
        return (values - self._zero_shift) * \
               (self.pixel_max - self.pixel_min) / self._range # pixel_factor

    def trim(self, value):
        """trims value to the range, ie. set to min or max if <min or > max """
        if value < self.min:
            return self.min
        elif value > self.max:
            return self.max
        return value

