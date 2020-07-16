# -*- coding: utf-8 -*-

"""
Expyriment convinient functions for the force DAQ remote control

(c) O. Lindemann

for two sensor setups

"""

from expyriment import misc, control, stimuli, io
from . import remote_control as rc


FORCE_SERVER_IP = "192.168.1.2"
WEAK, FINE, STRONG = [0, 1, 2]
STR_FULL_FORCE = u"kräftig" 
STR_LESS_FORCE = u"sacht"

stopwatch = misc.Clock()
udp = rc.init_udp_connection()
print(udp)


def runtimeerror(exp, text):
    stimuli.TextScreen("ERROR", text).present()
    exp.keyboard.wait()
    control.end()
    udp.send(rc.Command.QUIT)
    exit()


def start(exp, time_for_feedback=10):
    """ returns true if feedback is OK
    waits a particular time (in sec) for feedback and
    """

    udp.send(rc.Command.START)
    stopwatch.reset_stopwatch()
    while True:
        rtn = udp.poll()
        exp.keyboard.check()
        if rtn == rc.Command.FEEDBACK_STARTED:
            break
        if stopwatch.stopwatch_time > time_for_feedback * 1000:
            return False
    return True


def pause(exp, time_for_feedback=60 * 2):
    """returns true if feedback is OK
    waits a particular for feedback and
    """

    udp.send(rc.Command.PAUSE)
    stopwatch.reset_stopwatch()
    while True:
        rtn = udp.poll()
        exp.keyboard.check()
        if rtn == rc.Command.FEEDBACK_PAUSED:
            break
        if stopwatch.stopwatch_time > time_for_feedback * 1000:
            return False
    return True


# make connection #
def make_connection(exp, experiment_name="force_daq"):
    """hand shake and filename,
    returns forceDAQ version
    """

    stimuli.TextScreen("Prepare force recording", "press key if ready").present()
    exp.keyboard.wait()
    stimuli.BlankScreen().present()
    while not udp.connect_peer(FORCE_SERVER_IP):
        stimuli.TextScreen("ERROR while connecting to server",
                           "try again or <ESC> to quit").present()
        exp.keyboard.wait()
        stimuli.BlankScreen().present()
        exp.clock.wait(300)

    stimuli.TextScreen("Connected", "").present()
    exp.clock.wait(500)
    udp.send(rc.Command.FILENAME.decode('utf-8', 'replace') + "{0}_{1}.csv".format(experiment_name, exp.subject))
    rtn = udp.receive(5)  # paused
    if rtn is None:
        runtimeerror(exp, "Force server not responding")
    version = rc.get_data(rc.Command.GET_VERSION)
    stimuli.TextScreen("Connected", "Version " + version).present()
    exp.clock.wait(1000)
    return version


def force_button_box_prepare(n_sensors=1):
    udp.clear_receive_buffer()
    udp.send(rc.Command.SET_LEVEL_CHANGE_DETECTION)
    if n_sensors>1:
        udp.send(rc.Command.SET_LEVEL_CHANGE_DETECTION2)


def force_button_box_check():
    """
    changes to level
    """
    evt, level = rc.poll_multiple_events([rc.Command.CHANGED_LEVEL, rc.Command.CHANGED_LEVEL2])
    if evt is not None:
        if evt == rc.Command.CHANGED_LEVEL:
            sensor = 1
        else:
            sensor = 2
        return (sensor, level)
    return (None, None)


def force_button_box_wait(exp, duration=None, minimum_level=-1):
    """
    returns if one of two sensors changes its level
    """

    stopwatch.reset_stopwatch()
    last_key = None
    rt = None
    force_button_box_prepare()
    while not(duration is not None and stopwatch.stopwatch_time > duration):
        sensor, level = force_button_box_check()
        if sensor is not None:
            if level>=minimum_level:
                rt = stopwatch.stopwatch_time
                break
            else:
                force_button_box_prepare()
                sensor = None
        last_key = exp.keyboard.check()
        if last_key is not None:
            break

    return sensor, level, rt, last_key


def wait_no_button_pressed(exp, feedback_stimulus=None, polling_intervall=500):
    """level detection needs to be switch on
    display feedback_stimulus (optional) if one button pressed
    """
    if rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0 or \
                    rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0:
        if feedback_stimulus is not None:
            feedback_stimulus.present()
        while rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0 or \
                        rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0:
            exp.keyboard.wait(duration=polling_intervall)


############ further convenient functions
def hold_check(exp, holding_time, background_stimulus=None,
               n_sensors=2): # FIXME not checked for sensor=1
    if background_stimulus is None:
        background_stimulus = stimuli.BlankScreen()

    background_stimulus.present()
    background_stimulus.present()
    udp.send("hold:test")

    fine = stimuli.Circle(radius=20, colour=misc.constants.C_GREY, line_width=0)
    too_low = stimuli.Circle(radius=20, colour=misc.constants.C_GREEN, line_width=0)
    too_strong = stimuli.Circle(radius=20, colour=misc.constants.C_RED, line_width=0)
    bkg = [stimuli.Circle(position=(-200, 0), radius=24, colour=misc.constants.C_BLACK, line_width=0),
           stimuli.Circle(position=(200, 0), radius=24, colour=misc.constants.C_BLACK, line_width=0)]

    key = None
    stopwatch.reset_stopwatch()

    while key is None and stopwatch.stopwatch_time < holding_time:
        key = exp.keyboard.check()
        udp.clear_receive_buffer()
        lv = [rc.get_data(rc.Command.GET_THRESHOLD_LEVEL),
              rc.get_data(rc.Command.GET_THRESHOLD_LEVEL2)]
        for i in range(n_sensors):
            bkg[i].clear_surface()
            if lv[i] == WEAK:
                too_low.plot(bkg[i])
                stopwatch.reset_stopwatch()
            elif lv[i] == STRONG:
                too_strong.plot(bkg[i])
                stopwatch.reset_stopwatch()
            elif lv[i] == FINE:
                fine.plot(bkg[i])
            bkg[i].present(clear=False, update=False)
            bkg[i].present(clear=False, update=False)
        exp.screen.update()

    background_stimulus.present()

def _text2number_array(txt):
    """helper function for textinput_thesholds """
    rtn = []
    try:
        for x in txt.split(","):
            rtn.append(float(x))
        return rtn
    except:
        return None


def textinput_thesholds(message="Enter thresholds"):
    thresholds = _text2number_array(io.TextInput(message=message).get())
    stimuli.BlankScreen().present()
    if thresholds is not None:
        if len(thresholds) != 2:
            thresholds = None
    return thresholds


def threshold_menu(exp, thresholds, last_item="Ende"):
    while True:
        select = io.TextMenu(heading=u"Schwellen: " + str(thresholds),
                             menu_items=["Schwellen Anpassen ",  # 0
                                         "Halten",  # 1
                                         last_item],
                             background_colour=misc.constants.C_GREY,
                             text_colour=misc.constants.C_BLACK,
                             width=500)
        x = select.get()
        blank = stimuli.BlankScreen()
        blank.present()

        if x == 0:
            new = textinput_thesholds()
            if new is not None:
                thresholds = new
        elif x == 1:
            if not start(exp):
                stimuli.TextScreen("ERROR: Could not start recording",
                                   "Press key to quit").present()
                exp.keyboard.wait()
                exit()
            exp.clock.wait(500)
            rc.set_force_thresholds(lower=thresholds[0], upper=thresholds[1])
            hold_check(exp, holding_time=10000)
            blank.present()
            pause(exp)
        else:
            break

    return thresholds
