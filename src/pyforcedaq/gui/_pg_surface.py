import pygame
from expyriment.stimuli import Canvas

class PGSurface(Canvas):
    """PyGame Surface: Expyriment Stimulus for direct Pygame operations and
    PixelArrays

    In contrast to other Expyriment stimuli the class does not generate temporary
    surfaces.
    """

    def __init__(self, size, position=None, colour=None):
        Canvas.__init__(self, size, position, colour)
        self._px_array = None

    @property
    def surface(self):
        """DOC"""
        if not self.has_surface:
            ok = self._set_surface(self._get_surface())  # create surface
            if not ok:
                raise RuntimeError("Cannot call surface on compressed stimuli!")
        return self._surface

    @property
    def pixel_array(self):
        """DOC"""
        if self._px_array is None:
            self._px_array = pygame.PixelArray(self.surface)
        return self._px_array

    @pixel_array.setter
    def pixel_array(self, value):
        if self._px_array is None:
            self._px_array = pygame.PixelArray(self.surface)
        self._px_array = value

    def unlock_pixel_array(self):
        """DOC"""
        self._px_array = None

    def preload(self, inhibit_ogl_compress=False):
        self.unlock_pixel_array()
        return Canvas.preload(self, inhibit_ogl_compress)

    def compress(self):
        self.unlock_pixel_array()
        return Canvas.compress(self)

    def decompress(self):
        self.unlock_pixel_array()
        return Canvas.decompress(self)

    def plot(self, stimulus):
        self.unlock_pixel_array()
        return Canvas.plot(self, stimulus)

    def clear_surface(self):
        self.unlock_pixel_array()
        return Canvas.clear_surface(self)

    def copy(self):
        self.unlock_pixel_array()
        return Canvas.copy(self)

    def unload(self, keep_surface=False):
        if not keep_surface:
            self.unlock_pixel_array()
        return Canvas.unload(self, keep_surface)

    def rotate(self, degree, filter=True):  # Exypriment >=.9
        self.unlock_pixel_array()
        return Canvas.rotate(self, degree, filter)

    def scale(self, factors):
        self.unlock_pixel_array()
        return Canvas.scale(self, factors)

    # expyriment 0.8.0
    # def scale_to_fullscreen(self, keep_aspect_ratio=True):
    # self.unlock_pixel_array()
    # return Canvas.scale_to_fullscreen(self, keep_aspect_ratio)

    def flip(self, booleans):
        self.unlock_pixel_array()
        return Canvas.flip(self, booleans)

    def blur(self, level):
        self.unlock_pixel_array()
        return Canvas.blur(self, level)

    def scramble(self, grain_size):
        self.unlock_pixel_array()
        return Canvas.scramble(self, grain_size)

    def add_noise(self, grain_size, percentage, colour):
        self.unlock_pixel_array()
        return Canvas.add_noise(self, grain_size, percentage, colour)


