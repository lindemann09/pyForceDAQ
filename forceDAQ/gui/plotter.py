__version__ = "0.3"

import threading
import numpy as np
import pygame
try:
    # expyriment >= 0.10
    from expyriment.misc import Colour as ExpyColor
except:
    # old expyriment
    ExpyColor = tuple

from ._pg_surface import PGSurface

lock_expyriment = threading.Lock()
Numpy_array_type = type(np.array([]))

class Plotter(PGSurface):
    """Pygame Plotter"""

    def __init__(self, n_data_rows, data_row_colours,
                 width=600, y_range=(-100, 100),
                 background_colour=(180, 180, 180),
                 marker_colour=(200, 200, 200),
                 position=None,
                 axis_colour=None):
        self._n_data_rows = n_data_rows
        self._data_row_colours = check_colour_array(values=data_row_colours,
                                            required_n_colours=n_data_rows)
        self._y_range = y_range
        height = self._y_range[1] - self._y_range[0]

        self._background_colour = tuple(background_colour)
        self._marker_colour = tuple(marker_colour)
        self._horizontal_lines = None

        if axis_colour is None:
            self.axis_colour = background_colour
        else:
            self.axis_colour = axis_colour
        self._previous = [None] * n_data_rows
        PGSurface.__init__(self, size=(width, height),
                           position=position)
        self.clear_area()

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    def clear_area(self):
        self.pixel_array[:, :] = self._background_colour


    def set_horizontal_line(self, y_values):
        """y_values: array"""
        try:
            self._horizontal_lines = np.array(y_values, dtype=int)
        except:
            self._horizontal_lines = None

    def write_values(self, position, values, set_marker=False,
                     set_point_marker=False):
        """
        additional points: np.array
        """

        if set_marker:
            self.pixel_array[position, :] = self._marker_colour
        else:
            self.pixel_array[position, :] = self._background_colour

        if set_point_marker:
            self.pixel_array[position, 0:2] = self._marker_colour


        if self._horizontal_lines is not None:
            for c in (self._y_range[1] - self._horizontal_lines):
                self.pixel_array[:, c:c+1] = self._marker_colour

        for c, plot_value in enumerate(self._y_range[1] - \
                np.array(values, dtype=int)):
            if plot_value >= 0 and self._previous[c] >= 0 \
                    and plot_value <= self._height and \
                            self._previous[c] <= self._height:
                if self._previous[c] > plot_value:
                    self.pixel_array[position,
                    plot_value:self._previous[c] + 1] = \
                        self._data_row_colours[c]
                else:
                    self.pixel_array[position,
                    self._previous[c]:plot_value + 1] = \
                        self._data_row_colours[c]
            self._previous[c] = plot_value

    def add_values(self, values, set_marker=False):
        """ high level function of write values with type check and shifting to left
        not used by plotter thread
        """
        if type(values) is not Numpy_array_type and \
                not isinstance(values, tuple) and \
                not isinstance(values, list):
            values = [values]
        if len(values) != self._n_data_rows:
            raise RuntimeError('Number of data values does not match the ' +
                               'defined number of data rows!')

        # move plot one pixel to the left
        self.pixel_array[:-1, :] = self.pixel_array[1:, :]
        self.write_values(position=-1, values=values, set_marker=set_marker)


class PlotterThread(threading.Thread):
    def __init__(self, n_data_rows, data_row_colours,
                 width=600, y_range=(-100, 100),
                 background_colour=(80, 80, 80),
                 marker_colour=(200, 200, 200),
                 position=None,
                 axis_colour=None):
        super(PlotterThread, self).__init__()
        self._plotter = Plotter(n_data_rows=n_data_rows,
                                data_row_colours=data_row_colours,
                                width=width, y_range=y_range,
                                background_colour=background_colour,
                                marker_colour=marker_colour,
                                position=position,
                                axis_colour=axis_colour)
        self._new_values = []
        self._lock_new_values = threading.Lock()
        self._running = threading.Event()
        self._stop_request = threading.Event()
        self._clear_area_event = threading.Event()
        self.unpause()

    def get_plotter_rect(self, screen_size):
            half_screen_size = (screen_size[0] / 2, screen_size[1] / 2)
            pos = self._plotter.absolute_position
            stim_size = self._plotter.surface_size
            rect_pos = (pos[0] + half_screen_size[0] - stim_size[0] / 2,
                            - pos[1] + half_screen_size[1] - stim_size[1] / 2)
            return pygame.Rect(rect_pos, stim_size)

    def clear_area(self):
        self._clear_area_event.set()

    def pause(self):
        self._running.clear()

    def unpause(self):
        self._running.set()

    def stop(self):
        self.join()

    def join(self, timeout=None):
        self._stop_request.set()
        super(PlotterThread, self).join(timeout)

    def run(self):
        """the plotter thread is constantly updating the the
        pixel_area"""

        while not self._stop_request.is_set():

            if not self._running.is_set():
                self._running.wait(timeout=1)
                continue

            if self._clear_area_event.is_set():
                self._plotter.clear_area()
                self._clear_area_event.clear()

            # get data
            if self._lock_new_values.acquire(False):
                values = self._new_values
                self._new_values = []
                self._lock_new_values.release()  # release to receive new values
            else:
                values = []

            n = len(values)
            if n > 0:
                if n > self._plotter.width:
                    values = values[-1 * self._plotter.width:]  # only the last
                    n = len(values)
                self._plotter.pixel_array[:-1 * n, :] = \
                    self._plotter.pixel_array[n:, :]
                for x in range(-1 * n, 0):
                    self._plotter.write_values(position=x,
                                               values=values[x][0],
                                               set_marker=values[x][1],
                                               set_point_marker=values[x][2])
                # Expyriment present
                lock_expyriment.acquire()
                self._plotter.present(update=False, clear=False)
                lock_expyriment.release()

    def set_horizontal_lines(self, y_values):
        """adds new values to the plotter
        y_values has to be an array
        """
        self._lock_new_values.acquire()
        self._plotter.set_horizontal_line(y_values=y_values)
        self._lock_new_values.release()

    def add_values(self, values, set_marker=False, set_point_marker=False):
        """adds new values to the plotter"""
        self._lock_new_values.acquire()
        self._new_values.append((values, set_marker, set_point_marker))
        self._lock_new_values.release()


## helper
def check_colour_array(values, required_n_colours):
    """ check if it is a list of colours list of colours,
    otherwise raise an error
    """
    try:
        if not isinstance(values[0], (list, tuple, ExpyColor) ):
            # it is a list, but the elements are not colours, let's assume
            # it is one dimensional array
            values = [values]
    except:
        values = [()]  # values is not list pixel_array

    values = list(map(lambda x:tuple(x), values)) # force list of tuples

    if len(values) != required_n_colours:
        raise RuntimeError('Number of data row colour does not match the ' +
                           'defined number of data rows!')
    return values
