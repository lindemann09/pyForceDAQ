__author__ = 'Oliver Lindemann'

# helper functions
from time import strftime
import pygame

from expyriment import stimuli
from expyriment.misc import constants

from forceDAQ import __version__ as forceDAQVersion


colours = [constants.C_RED,
               constants.C_GREEN,
               constants.C_YELLOW,
               constants.C_BLUE,
               constants.C_EXPYRIMENT_ORANGE,
               constants.C_EXPYRIMENT_PURPLE]

def get_pygame_rect(stimulus, screen_size):
    """little helper function that returns the pygame rect from stimuli"""
    half_screen_size = (screen_size[0] / 2, screen_size[1] / 2)
    pos = stimulus.absolute_position
    stim_size = stimulus.surface_size
    rect_pos = (pos[0] + half_screen_size[0] - stim_size[0] / 2,
                - pos[1] + half_screen_size[1] - stim_size[1] / 2)
    return pygame.Rect(rect_pos, stim_size)

def logo_text_line(text):
    blank = stimuli.Canvas(size=(600, 400))
    stimuli.TextLine(text="Version " + forceDAQVersion, position=(0, 80),
                     text_size=14,
                     text_colour=constants.C_EXPYRIMENT_ORANGE).plot(blank)
    stimuli.TextLine(text=text).plot(blank)
    return blank

class RecordingScreen(object):
    def __init__(self, window_size, filename, remote_control):
        """Expyriment has to be intialized"""
        margin = 30
        self.left = -1*window_size[0]/2 + margin
        self.right = window_size[0]/2 - margin
        self.top = window_size[1]/2 - margin
        self.bottom = -1*window_size[1]/2 + margin

        self.elements = []
        self.add_text_line_left("Force Recorder " + str(forceDAQVersion),
                                [self.left, self.top], text_size=15)
        self.add_text_line_left("(p) pause/unpause", [self.left, self.bottom])
        self.add_text_line_left("(v) switch view", [self.left + 160, self.bottom +20])
        self.add_text_line_left("(f) switch filtered", [self.left + 160, self.bottom])
        self.add_text_line_left("(+/-): axes scaling", [self.left + 340, self.bottom + 20])
        self.add_text_line_left("(up/down): axes shift", [self.left + 340, self.bottom])
        self.add_text_line_left("(t): change thresholds", [self.left + 560, self.bottom])
        self.add_text_line_right("(q) quit recording", [self.right, self.bottom ])
        self.add_text_line_centered("file: " + filename, [0, self.top], text_size=15)
        if remote_control:
            self.add_text_line_centered("REMOTE CONTROL", [0, self.top-20], text_size=15)
        self.add_text_line_right("date: {0}".format(strftime("%d/%m/%Y")),
                                [self.right, self.top], text_size=15)

    @staticmethod
    def _text_line(text, position, text_size=12, text_colour=(255, 150, 50)):
        """helper function"""
        return stimuli.TextLine(text, position=position,
                                text_size=text_size,
                                text_colour=text_colour)

    def add_text_line_centered(self, text, position, text_size=12,
                               text_colour=(255, 150, 50)):
        self.elements.append(RecordingScreen._text_line(text, position,
                                                       text_size,
                                                       text_colour))

    def add_text_line_right(self, text, position, text_size=12,
                            text_colour=(255, 150, 50)):
        """text_line right aligned"""
        txt = RecordingScreen._text_line(text, position, text_size,
                                        text_colour)
        txt.move((-1 * (txt.surface_size[0] / 2), 0))
        self.elements.append(txt)

    def add_text_line_left(self, text, position, text_size=12,
                           text_colour=(255, 150, 50)):
        """text line left aligned"""
        txt = RecordingScreen._text_line(text, position, text_size,
                                        text_colour)
        txt.move((txt.surface_size[0] / 2, 0))
        self.elements.append(txt)

    def stimulus(self, infotext=""):
        """Return the stimulus including infotext (obligatory)"""
        canvas = stimuli.BlankScreen()
        for elem in self.elements:
            elem.plot(canvas)
        if len(infotext) > 0:
            RecordingScreen._text_line(text=infotext, position=[0, 0],
                                      text_size=36).plot(canvas)
        return canvas

