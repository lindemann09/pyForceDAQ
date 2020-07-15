import numpy as np
from expyriment.stimuli import Canvas, Rectangle, TextLine
from expyriment.misc import constants

def level_indicator(value, text, scaling, width=20,
                    text_size=14, text_gap=20,  position=(0,0), thresholds = None,
                    colour=constants.C_EXPYRIMENT_ORANGE):
    """make an level indicator in for of an Expyriment stimulus

    text_gap: gap between indicator and text
    scaling: Scaling object

    Returns
    --------
    expyriment.Canvas

    """

    value = scaling.trim(value)

    # indicator
    height = scaling.pixel_max - scaling.pixel_min
    indicator = Canvas(size=(width + 2, height + 2),
                               colour=(30, 30, 30))

    zero = scaling.data2pixel(0)
    px_bar_height = scaling.data2pixel(value) - zero
    bar = Rectangle(size=(width, abs(px_bar_height)),
                            position=(0, zero + int((px_bar_height + 1) / 2)),
                            colour=colour)
    bar.plot(indicator)

    # levels & horizontal lines
    try:
        px_horizontal_lines = scaling.data2pixel(values=np.array(thresholds.thresholds))
    except:
        px_horizontal_lines = None
    if px_horizontal_lines is not None:
        for px in px_horizontal_lines:
            level = Rectangle(size=(width+6, 2),
                            position=(0, px),
                            colour=constants.C_WHITE)
            level.plot(indicator)




    # text labels
    txt = TextLine(text=text, text_size=text_size,
                           position=(0, -1 * (int(height / 2.0) + text_gap)),
                           text_colour=constants.C_YELLOW)

    # make return canvas
    w = max(txt.surface_size[0], indicator.size[0])
    h = height + 2 * (txt.surface_size[1]) + text_gap
    rtn = Canvas(size=(w, h), colour=(0, 0, 0), position=position)
    indicator.plot(rtn)
    txt.plot(rtn)
    return rtn
