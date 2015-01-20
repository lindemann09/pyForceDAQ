"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from time import sleep
import pygame
from cPickle import dumps
import numpy as np
from expyriment import control, design, stimuli, io, misc

from forceDAQ.recorder import DataRecorder, SensorSettings
from forceDAQ.types import ForceData
from forceDAQ.types import GUIRemoteControlCommands as RcCmd
from forceDAQ.misc import Timer, SensorHistory

from plotter import PlotterThread, level_indicator
from layout import logo_text_line, RecordingScreen, colours, get_pygame_rect

def initialize(exp, remote_control=None, filename=None):
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


def wait_for_start_recording_event(exp, udp_connection):
    if udp_connection is None:
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


def record_data(exp, recorder, filename, plot_indicator=False,
                start_paused=True, remote_control=True):
    """udp command:
            "start", "pause", "stop"
            "thresholds = [x,...]" : start level detection for Fz parameter and set threshold
            "thresholds stop" : stop level detection
    """

    refresh_interval = 200
    indicator_grid = 70  # distance between indicator center
    minVal = -70
    maxVal = +70
    scaling_plotting = 2.3

    pause_recording = start_paused
    last_recording_status = None
    set_marker = False

    gui_clock = misc.Clock()
    background = RecordingScreen(window_size = exp.screen.size,
                                           filename=filename)
    # plotter
    last_plotted_smpl = 0
    plotter_thread = PlotterThread(
                    n_data_rows=3,
                    data_row_colours=colours[:3],
                    y_range=(-250, 250),
                    width=900,
                    position=(0,-30),
                    background_colour=[10,10,10],
                    axis_colour=misc.constants.C_YELLOW)
    plotter_thread.start()

    exp.keyboard.clear()

    # TODO HARDCODED VARIABLES
    # one sensor only, paramter for level detection
    sensor_process = recorder._force_sensor_processes[0]
    level_detection_parameter = ForceData.forces_names.index("Fz")
    history = SensorHistory(history_size = 5, number_of_parameter=1)

    quit_recording = False
    while not quit_recording:

        if pause_recording:
            sleep(0.001)

        # process keyboard
        key = exp.keyboard.check(check_for_control_keys=False)
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            quit_recording = True
        if key == misc.constants.K_v:
            plot_indicator = not(plot_indicator)
            background.stimulus().present()
        if key == misc.constants.K_p:
            # pause
            pause_recording = not pause_recording

        # process udp
        udp = recorder.process_udp_events()
        while len(udp)>0:
            udp_event = udp.pop(0)
            set_marker = True

            #remote control
            if remote_control and \
                    udp_event.string.startswith(RcCmd.COMMAND_STR):
                if udp_event.string == RcCmd.START:
                    pause_recording = False
                    set_marker = False
                elif udp_event.string == RcCmd.PAUSE:
                    pause_recording = True
                    set_marker = False
                elif udp_event.string == RcCmd.THRESHOLDS:
                    quit_recording = True
                elif udp_event.string.startswith(RcCmd.THRESHOLDS):
                    try:
                        tmp = udp_event.string[len(RcCmd.THRESHOLDS):]
                        tmp = eval(tmp)
                    except:
                        tmp = None
                    if isinstance(tmp, list):
                        history.level_thresholds = tmp
                    else:
                        history.level_thresholds = [] # stop level detection
                elif udp_event.string == RcCmd.GET_FX:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fx))
                elif udp_event.string == RcCmd.GET_FY:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fy))
                elif udp_event.string == RcCmd.GET_FZ:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fz))
                elif udp_event.string == RcCmd.GET_TX:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fx))
                elif udp_event.string == RcCmd.GET_TY:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fy))
                elif udp_event.string == RcCmd.GET_TZ:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(sensor_process.Fz))


        # show pause or recording screen
        if pause_recording != last_recording_status:
            last_recording_status = pause_recording
            if pause_recording:
                background.stimulus("writing data...").present()
                recorder.pause_recording()
                background.stimulus("Paused recording").present()
                if remote_control:
                    recorder.udp.send_queue.put(RcCmd.FEEDBACK + "paused")
            else:
                recorder.start_recording()
                start_recording_time = gui_clock.time
                background.stimulus().present()
                if remote_control:
                    recorder.udp.send_queue.put(RcCmd.FEEDBACK + "started")

        # process new samples
        if last_plotted_smpl < sensor_process.sample_cnt: # new sample
            smpl = [sensor_process.Fx, sensor_process.Fy, sensor_process.Fz]
            # history
            history.update([ smpl[level_detection_parameter] ]) # TODO: single sensor only
            # level detection
            if len(history.level_thresholds) > 0:
                tmp = history.levels[0]
                if tmp > 0:
                    recorder.udp.send_queue.put(RcCmd.PICKLED_VALUE +
                                                dumps(tmp))

            # update plotter
            if not plot_indicator:
                plotter_thread.add_values(
                        values = np.array(smpl, dtype=float)  * scaling_plotting,
                        set_marker=set_marker)
                set_marker = False
                last_plotted_smpl = sensor_process.sample_cnt


        if not pause_recording and gui_clock.stopwatch_time >= refresh_interval:
            gui_clock.reset_stopwatch()

            update_rects = []
            if plot_indicator:
                ## indicator
                force_data_array = [sensor_process.Fx, sensor_process.Fy, sensor_process.Fz,
                                    sensor_process.Tx, sensor_process.Ty, sensor_process.Tz]
                for cnt in range(6):
                    x_pos = (-3 * indicator_grid) + (cnt * indicator_grid) + 0.5*indicator_grid
                    li = level_indicator(value=force_data_array[cnt],
                                         text=ForceData.forces_names[cnt],
                                         minVal=minVal, maxVal=maxVal, width = 50,
                                         position=(x_pos,0) )
                    li.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(li, exp.screen.size))

                #line
                rect = stimuli.Line(start_point=(-200,0), end_point=(200,0),
                                    line_width=1, colour=misc.constants.C_YELLOW)
                rect.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(rect, exp.screen.size))

                # axis labels
                pos = (-220, -145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position=pos, text = str(minVal),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                pos = (-220, 145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position= pos, text = str(maxVal),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                # end indicator
            else:
                # plotter
                update_rects.append(
                    plotter_thread.get_plotter_rect(exp.screen.size))

            # counter
            pos = (-370, 250)
            stimuli.Canvas(position=pos, size=(400,60),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextBox(position= pos,
                                size = (400, 60),
                                #background_colour=(30,30,30),
                                text_size=15,
                                text = "n samples recorder: {0}\n".format(
                                                    sensor_process.sample_cnt) +
                                       "n samples buffered: {0} ({1} seconds)".format(
                                    sensor_process.buffer_size,
                                    (gui_clock.time - start_recording_time)/1000),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            pygame.display.update(update_rects)
            # end refesh screen

        # end while recording

    background.stimulus("Quitting").present()
    plotter_thread.stop()
    recorder.pause_recording()

def start():
    # expyriment
    control.defaults.initialize_delay = 0
    control.defaults.pause_key = None
    control.defaults.window_mode = True
    control.defaults.window_size = (1000, 700)
    control.defaults.fast_quit = True
    control.defaults.open_gl = False
    control.defaults.event_logging = 0
    exp = design.Experiment()
    exp.set_log_level(0)

    SENSOR_ID = 1  # i.e., NI-device id

    remote_control, filename = initialize(exp, filename="output")
    timer = Timer()
    sensor1 = SensorSettings(device_id=SENSOR_ID, sync_timer=timer,
                                    calibration_file="FT_demo.cal")
    recorder = DataRecorder([sensor1], poll_udp_connection=True)
    recorder.open_data_file(filename, directory="data", suffix=".csv",
                        time_stamp_filename=False, comment_line="")

    stimuli.TextLine("Press key to determine bias").present()
    exp.keyboard.wait()
    stimuli.BlankScreen().present()
    recorder.determine_biases(n_samples=500)

    if remote_control:
        pass
    else:
        stimuli.TextLine("Press key to start recording").present()
        exp.keyboard.wait()

    record_data(exp, recorder=recorder,
                    filename=filename,
                    plot_indicator = True,
                    start_paused=True,
                    remote_control=remote_control)

    recorder.quit()
