__author__ = "Oliver Lindemann"

# helper functions
import os
from typing import List

import pygame
from expyriment import stimuli
from expyriment.misc import constants as expy_constants

from .. import __version__ as forceDAQVersion

colours = [
    expy_constants.C_RED,
    expy_constants.C_GREEN,
    expy_constants.C_YELLOW,
    expy_constants.C_BLUE,
    expy_constants.C_EXPYRIMENT_ORANGE,
    expy_constants.C_EXPYRIMENT_PURPLE,
]

def get_pygame_rect(stimulus, screen_size):
    """little helper function that returns the pygame rect from stimuli"""
    half_screen_size = (screen_size[0] / 2, screen_size[1] / 2)
    pos = stimulus.absolute_position
    stim_size = stimulus.surface_size
    rect_pos = (
        pos[0] + half_screen_size[0] - stim_size[0] / 2,
        -pos[1] + half_screen_size[1] - stim_size[1] / 2,
    )
    return pygame.Rect(rect_pos, stim_size)



def logo_text_line(text):
    blank = stimuli.Canvas(size=(600, 400))
    logo = stimuli.Picture(
        filename=os.path.join(os.path.dirname(__file__), "forceDAQ_logo.png"),
        position=(0, 150),
    )
    logo.scale(0.6)
    make_text_line(
        text="Version " + forceDAQVersion,
        position=(0, 80),
        text_size=14,
        text_colour=expy_constants.C_EXPYRIMENT_ORANGE,
    ).plot(blank)
    logo.plot(blank)
    make_text_line(text=text, position=(0, 0), text_size=12, text_colour=expy_constants.C_WHITE).plot(blank)
    return blank

def make_text_line(text, position, text_size, text_colour):
    """helper function"""
    return stimuli.TextLine(text, position=position, text_size=text_size,
                            text_colour=text_colour, text_font="Courier")


class RecordingScreen(object):

    def __init__(self, window_size,
                 txt_top_left: List[str],
                 txt_top_center:str,
                 txt_top_right:str,
                 text_colour,
                 no_pause_option:bool = False):
        # NOTE: Expyriment has to be intialized
        margin = 30
        self.left = -1 * window_size[0] / 2 + margin
        self.right = window_size[0] / 2 - margin
        self.top = window_size[1] / 2 - margin
        self.bottom = -1 * window_size[1] / 2 + margin

        self.text_colour = text_colour
        self.elements = []

        for cnt, txt in enumerate(txt_top_left):
            self.add_text_line_left(
                txt,
                [self.left, self.top - cnt * 20],
                text_size=15,text_colour=None)
        col = expy_constants.C_GREY
        if not no_pause_option:
            self.add_text_line_left("P: pause/unpause saving", [self.left, self.bottom + 20], text_colour=col)
        self.add_text_line_left("B: set baseline", [self.left, self.bottom], text_colour=col)
        self.add_text_line_left("V: toggle view", [self.left + 190, self.bottom + 20], text_colour=col)
        self.add_text_line_left("F: toggle show filtered", [self.left + 190, self.bottom], text_colour=col)
        self.add_text_line_left(
            "+/-: axes scaling", [self.left + 380, self.bottom + 20], text_colour=col
        )
        self.add_text_line_left("up/down: axes shift", [self.left + 380, self.bottom], text_colour=col)
        self.add_text_line_left(
            "T: change thresholds", [self.left + 580, self.bottom], text_colour=col
        )
        self.add_text_line_right("Q: quit recording", [self.right, self.bottom], text_colour=col)

        self.add_text_line_right(txt_top_right, [self.right, self.top], text_size=15)
        self.add_text_line_centered(txt_top_center, [0, self.top], text_size=15)

    def add_text_line_centered(
        self, text, position, text_size=12, text_colour=None
    ):
        if text_colour is None:
            text_colour = self.text_colour
        self.elements.append(
            make_text_line(text, position, text_size, text_colour)
        )

    def add_text_line_right(
        self, text, position, text_size=12, text_colour=None
    ):
        """text_line right aligned"""
        if text_colour is None:
            text_colour = self.text_colour
        txt = make_text_line(text, position, text_size, text_colour)
        txt.move((-1 * (txt.surface_size[0] / 2), 0))
        self.elements.append(txt)

    def add_text_line_left(
        self, text, position, text_size=12, text_colour=None
    ):
        """text line left aligned"""
        if text_colour is None:
            text_colour = self.text_colour
        txt = make_text_line(text, position, text_size, text_colour)
        txt.move((txt.surface_size[0] / 2, 0))
        self.elements.append(txt)

    def stimulus(self, infotext=""):
        """Return the stimulus including infotext (obligatory)"""
        canvas = stimuli.BlankScreen()
        for elem in self.elements:
            elem.plot(canvas)
        if len(infotext) > 0:
            make_text_line(
                text=infotext, position=[0, 0], text_size=36,
                text_colour=self.text_colour
            ).plot(canvas)
        return canvas
