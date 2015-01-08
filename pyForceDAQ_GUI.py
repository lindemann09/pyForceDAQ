"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from forceDAQ import __version__

import pygame
from time import strftime
from expyriment import control, design, stimuli, io, misc
from forceDAQ.recorder import DataRecorder, Clock, SensorSettings

def logo_text_line(text):
    blank = stimuli.Canvas(size=(600, 400))
    stimuli.TextLine(text="Version " + __version__, position=(0, 80),
                     text_size=14,
                     text_colour=misc.constants.C_EXPYRIMENT_ORANGE).plot(blank)
    stimuli.TextLine(text=text).plot(blank)
    return blank


def initialize(remote_control = None, filename = None):
    global exp
    control.initialize(exp)
    exp.mouse.show_cursor()

    if remote_control is None:
        logo_text_line(text="Use remote control? (y/N)").present()
        key = exp.keyboard.wait([ord("z"), ord("y"), ord("n"),
                                 misc.constants.K_SPACE,
                                 misc.constants.K_RETURN])[0]
        if key == ord("y") or key == ord("z"):
            remote_control = True
        else:
            remote_control = False

    if filename is None:
        bkg = logo_text_line("")
        filename = io.TextInput("Filename", background_stimulus=bkg).get()
        filename = filename.replace(" ", "_")

    return remote_control, filename


def wait_for_start_recording_event(remote_control):
    if remote_control:
        udp_connection.poll_last_data()  #clear buffer
        stimuli.TextLine(text="Waiting to UDP start trigger...").present()
        s = None
        while s is None or not s.lower().startswith('start'):
            exp.keyboard.check()
            s = udp_connection.poll()
        udp_connection.send('confirm')
    else:
        stimuli.TextLine(text
                         ="Press key to start recording").present()
        exp.keyboard.wait()



def record_data(remote_control, recorder):
    refresh_interval = 200
    indicator_grid = 70  # distance between indicator center
    indicator_labels = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    minVal = -70
    maxVal = +70

    refresh_timer = misc.Clock()

    background = RecordingScreen(window_size = exp.screen.size,
                                           filename=filename)
    background.stimulus(infotext="").present()

    exp.keyboard.clear()
    recorder.start_recording()
    pause_recording = False
    set_marker = False

    while True:

        # process keyboard
        key = exp.keyboard.check(check_for_control_keys=False)
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            break
        if key == misc.constants.K_p:
            # pause
            pause_recording = not pause_recording
            if pause_recording:
                recorder.pause_recording()
                background.stimulus("Paused recording").present()
            else:
                recorder.start_recording()
                background.stimulus().present()


        if not pause_recording and refresh_timer.stopwatch_time >= refresh_interval:
            refresh_timer.reset_stopwatch()


            #get last ForceData
            data = recorder.process_sensor_input()
            if len(data)>0:
                force_data = data[-1]
            else:
                continue

            update_rects = []
            force_data_array = force_data.force_np_array
            for cnt in range(6):
                x_pos = (-3 * indicator_grid) + (cnt * indicator_grid) + 0.5*indicator_grid
                li = level_indicator(value=force_data_array[cnt],
                                     text=indicator_labels[cnt],
                                    minVal=minVal, maxVal=maxVal, width = 50,
                                     position=(x_pos,0) )
                li.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(li))

            #line
            rect = stimuli.Line(start_point=(-200,0), end_point=(200,0),
                                line_width=1, colour=misc.constants.C_YELLOW)
            rect.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(rect))

            # axis labels
            pos = (-220, -145)
            stimuli.Canvas(position=pos, size=(30,20),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextLine(position=pos, text = str(minVal),
                        text_size=15, text_colour=misc.constants.C_YELLOW)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt))
            pos = (-220, 145)
            stimuli.Canvas(position=pos, size=(30,20),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextLine(position= pos, text = str(maxVal),
                        text_size=15, text_colour=misc.constants.C_YELLOW)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt))

            # counter
            pos = (-300, 200)
            stimuli.Canvas(position=pos, size=(300,20),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextLine(position= pos,
                                text = "n samples: {0}".format(
                                    recorder.sample_counter[force_data.device_id]),
                                text_size=15,
                                text_colour=misc.constants.C_YELLOW)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt))

            pygame.display.update(update_rects)


    recorder.pause_recording()


def get_pygame_rect(stimulus):
    """little helper function that returns the pygame rect from stimuli"""
    screen_size = exp.screen.size
    half_screen_size = (screen_size[0] / 2, screen_size[1] / 2)
    pos = stimulus.absolute_position
    stim_size = stimulus.surface_size
    rect_pos = (pos[0] + half_screen_size[0] - stim_size[0] / 2,
                - pos[1] + half_screen_size[1] - stim_size[1] / 2)
    return pygame.Rect(rect_pos, stim_size)


def level_indicator(value, text, minVal=-100, maxVal=100, width=20, height=300,
                    text_size=14, text_gap=20,  position=(0,0),
                    colour=misc.constants.C_EXPYRIMENT_ORANGE):
    """make an level indicator in for of an Expyriment stimulus

    text_gap: gap between indicator and text

    Returns
    --------
    expyriment.Canvas

    """

    if value < minVal:
        value = minVal
    elif value > maxVal:
        value = maxVal

    # indicator
    indicator_size = [width + 2, height + 2]
    indicator = stimuli.Canvas(size=indicator_size,
                               colour=(30, 30, 30))
    px_level = value * height / float(maxVal - minVal)
    bar = stimuli.Rectangle(size=(width, abs(px_level)),
                            position=(0, int((px_level + 1) / 2.0)),
                            colour=colour)
    bar.plot(indicator)
    # text
    txt = stimuli.TextLine(text=text, text_size=text_size,
                           position=(0, -1 * (int(height / 2.0) + text_gap)),
                           text_colour=misc.constants.C_YELLOW)

    # make return canvas
    w = max(txt.surface_size[0], indicator_size[0])
    h = height + 2 * (txt.surface_size[1]) + text_gap
    rtn = stimuli.Canvas(size=(w, h), colour=(0, 0, 0), position=position)
    indicator.plot(rtn)
    txt.plot(rtn)
    return rtn



class RecordingScreen(object):
    def __init__(self, window_size, filename):
        """Expyriment has to be intialized"""
        margin = 50
        self.left = -1*window_size[0]/2 + margin
        self.right = window_size[0]/2 - margin
        self.top = window_size[1]/2 - margin
        self.bottom = -1*window_size[1]/2 + margin

        self.elements = []
        self.add_text_line_left("Force Recorder " + str(__version__),
                                [self.left, self.top])
        self.add_text_line_left("p: pause/unpause", [self.left, self.bottom])
        self.add_text_line_right("q: quit recording", [self.right, self.bottom])
        self.add_text_line_centered("filename: " + filename,
                                    [0, self.top])
        self.add_text_line_right("date: {0}".format(strftime("%d/%m/%Y")),
                                [self.right, self.top])

    @staticmethod
    def _text_line(text, position, text_size=15, text_colour=(255, 150, 50)):
        """helper function"""
        return stimuli.TextLine(text, position=position,
                                text_size=text_size,
                                text_colour=text_colour)

    def add_text_line_centered(self, text, position, text_size=15,
                               text_colour=(255, 150, 50)):
        self.elements.append(RecordingScreen._text_line(text, position,
                                                       text_size,
                                                       text_colour))

    def add_text_line_right(self, text, position, text_size=15,
                            text_colour=(255, 150, 50)):
        """text_line right aligned"""
        txt = RecordingScreen._text_line(text, position, text_size,
                                        text_colour)
        txt.move((-1 * (txt.surface_size[0] / 2), 0))
        self.elements.append(txt)

    def add_text_line_left(self, text, position, text_size=15,
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


if __name__ == "__main__":

    # expyriment
    control.defaults.initialize_delay = 0
    control.defaults.pause_key = None
    control.defaults.window_mode = True
    control.defaults.window_size = (800, 600)
    control.defaults.fast_quit = True
    control.defaults.open_gl = False
    control.defaults.event_logging = 0
    exp = design.Experiment()
    exp.set_log_level(0)
    udp_connection = None

    colours = [misc.constants.C_RED,
               misc.constants.C_GREEN,
               misc.constants.C_YELLOW,
               misc.constants.C_BLUE,
               misc.constants.C_EXPYRIMENT_ORANGE,
               misc.constants.C_EXPYRIMENT_PURPLE]

    SENSOR_ID = 1  # i.e., NI-device id


    remote_control, filename = initialize(remote_control=False,
                                          filename="output")
    clock = Clock()
    sensor1 = SensorSettings(device_id=SENSOR_ID, sync_clock=clock,
                                    calibration_file="FT_demo.cal")
    recorder = DataRecorder([sensor1], poll_udp_connection=False)
    filename = recorder.open_data_file(filename, directory="data", suffix=".csv",
                        time_stamp_filename=False, comment_line="")

    stimuli.TextLine("Press key to determine bias").present()
    exp.keyboard.wait()
    stimuli.BlankScreen().present()
    recorder.determine_biases(n_samples=500)

    stimuli.TextLine("Press key to start recording").present()
    exp.keyboard.wait()

    record_data(remote_control, recorder=recorder)

    recorder.quit()