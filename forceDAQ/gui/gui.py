"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import pygame
import numpy as np
from expyriment import control, design, stimuli, io, misc

from forceDAQ.recorder import DataRecorder, Clock, SensorSettings
from plotter import PlotterThread, level_indicator

from layout import logo_text_line, RecordingScreen, colours, get_pygame_rect

def initialize(exp, remote_control, filename):
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


def record_data(exp, recorder, filename, plot_indicator=False):
    refresh_interval = 200
    indicator_grid = 70  # distance between indicator center
    indicator_labels = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    minVal = -70
    maxVal = +70

    refresh_timer = misc.Clock()

    background = RecordingScreen(window_size = exp.screen.size,
                                           filename=filename)
    background.stimulus(infotext="").present()

    # plotter
    scaling_plotting = 2.3
    last_plotted_smpl = 0
    plotter_thread = PlotterThread(
                    n_data_rows=3,
                    data_row_colours=colours[:3],
                    y_range=(-250, 250),
                    width=900,
                    position=(0,0),
                    background_colour=[10,10,10],
                    axis_colour=misc.constants.C_YELLOW)
    plotter_thread.start()


    exp.keyboard.clear()
    recorder.start_recording()
    pause_recording = False
    set_marker = False

    sensor_process = recorder._force_sensor_processes[0] # FIXME ONE SENSOR ONLY

    while True:

        # process keyboard
        key = exp.keyboard.check(check_for_control_keys=False)
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            background.stimulus("Quitting").present()
            break
        if key == misc.constants.K_v:
            plot_indicator = not(plot_indicator)
            background.stimulus().present()
        if key == misc.constants.K_p:
            # pause
            pause_recording = not pause_recording
            if pause_recording:
                background.stimulus("writing data...").present()
                recorder.pause_recording()
                background.stimulus("Paused recording").present()
            else:
                recorder.start_recording()
                background.stimulus().present()

        if not plot_indicator: # plotter
            if last_plotted_smpl < sensor_process.sample_cnt: # new sample
                values = np.array([sensor_process.Fx, sensor_process.Fy,
                               sensor_process.Fz], dtype=float) * scaling_plotting
                plotter_thread.add_values(values=values)
                last_plotted_smpl = sensor_process.sample_cnt

        if not pause_recording and refresh_timer.stopwatch_time >= refresh_interval:
            refresh_timer.reset_stopwatch()

            update_rects = []
            if plot_indicator:
                ## indicator
                force_data_array = [sensor_process.Fx, sensor_process.Fy, sensor_process.Fz,
                                    sensor_process.Tx, sensor_process.Ty, sensor_process.Tz]
                for cnt in range(6):
                    x_pos = (-3 * indicator_grid) + (cnt * indicator_grid) + 0.5*indicator_grid
                    li = level_indicator(value=force_data_array[cnt],
                                         text=indicator_labels[cnt],
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
            pos = (-300, 270)
            stimuli.Canvas(position=pos, size=(300,20),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextLine(position= pos,
                                text_size=15,
                                text = "n samples (buffer): {0} ({1})".format(
                                    sensor_process.sample_cnt,
                                    sensor_process.buffer_size),
                                text_colour=misc.constants.C_YELLOW)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            pygame.display.update(update_rects)

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
    udp_connection = None

    SENSOR_ID = 1  # i.e., NI-device id

    remote_control, filename = initialize(exp, remote_control=False,
                                          filename="output")
    clock = Clock()
    sensor1 = SensorSettings(device_id=SENSOR_ID, sync_clock=clock,
                                    calibration_file="FT_demo.cal")
    recorder = DataRecorder([sensor1], poll_udp_connection=False)
    recorder.open_data_file(filename, directory="data", suffix=".csv",
                        time_stamp_filename=False, comment_line="")

    stimuli.TextLine("Press key to determine bias").present()
    exp.keyboard.wait()
    stimuli.BlankScreen().present()
    recorder.determine_biases(n_samples=500)

    stimuli.TextLine("Press key to start recording").present()
    exp.keyboard.wait()

    record_data(exp, recorder=recorder,
                    filename=filename, plot_indicator = True)

    recorder.quit()