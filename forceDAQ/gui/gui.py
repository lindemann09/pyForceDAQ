"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from time import sleep
import pygame
from cPickle import dumps, loads
import numpy as np

from expyriment import control, design, stimuli, io, misc
from forceDAQ import GUIRemoteControlCommands as RcCmd
from forceDAQ import ForceData, Timer, SensorHistory, DataRecorder, SensorSettings, Thresholds
from plotter import PlotterThread, level_indicator
from layout import logo_text_line, RecordingScreen, colours, get_pygame_rect


def _initialize(exp, remote_control=None):
    control.initialize(exp)
    exp.mouse.show_cursor()

    if remote_control is None:
        logo_text_line(text="Use remote control? (Y/n)").present()
        key = exp.keyboard.wait([ord("z"), ord("y"), ord("n"),
                                 misc.constants.K_SPACE,
                                 misc.constants.K_RETURN])[0]
        if key == ord("n"):
            remote_control = False
        else:
            remote_control = True

    return remote_control


#def wait_for_start_recording_event(exp, udp_connection):
#    if udp_connection is None:
#        udp_connection.poll_last_data()  #clear buffer
#        stimuli.TextLine(text="Waiting to UDP start trigger...").present()
#        s = None
#        while s is None or not s.lower().startswith('start'):
#            exp.keyboard.check()
#            s = udp_connection.poll()
#        udp_connection.send('confirm')
#    else:
#        stimuli.TextLine(text
#                         ="Press key to start recording").present()
#        exp.keyboard.wait()


def _record_data(exp, recorder, plot_indicator=False, remote_control=False):
    """udp command:
            "start", "pause", "stop"
            "thresholds = [x,...]" : start level detection for Fz parameter and set threshold
            "thresholds stop" : stop level detection
    """

    refresh_interval = 200
    indicator_grid = 70  # distance between indicator center

    data_range = (-50, 10)
    plotter_yrange = (-250, 250)
    plotter_scaling = (plotter_yrange[1] - plotter_yrange[0]) / float(data_range[1] - data_range[0])
    plotter_width = 900
    plotter_position = (0, -30)
    pause_recording = True
    last_recording_status = None
    last_udp_data = None
    set_marker = False

    gui_clock = misc.Clock()
    background = RecordingScreen(window_size = exp.screen.size,
                                           filename=recorder.filename,
                                           remote_control=remote_control)
    # plotter
    last_processed_smpl = 0
    smpl = None
    plotter_thread = None

    exp.keyboard.clear()

    # TODO HARDCODED VARIABLES
    # one sensor only, paramater for level detection
    sensor_process = recorder._force_sensor_processes[0]
    level_detection_parameter = ForceData.forces_names.index("Fz")
    history = SensorHistory(history_size = 5, number_of_parameter=1)
    threshold = None
    quit_recording = False
    while not quit_recording:

        if pause_recording:
            sleep(0.001)

        # process keyboard
        key = exp.keyboard.check(check_for_control_keys=False)
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            quit_recording = True
        elif key == misc.constants.K_v:
            plot_indicator = not(plot_indicator)
            background.stimulus().present()
            if plot_indicator:
                plotter_thread.pause()
            else:
                plotter_thread.unpause()

        elif key == misc.constants.K_p:
            # pause
            pause_recording = not pause_recording
        elif key == misc.constants.K_KP_MINUS and plotter_scaling < 15:
            data_range = (data_range[0] - 5, data_range[1] + 5)
            plotter_scaling = (plotter_yrange[1] - plotter_yrange[0]) / float(data_range[1] - data_range[0])
            background.stimulus().present()
            plotter_thread.clear_area()
        elif key == misc.constants.K_KP_PLUS:
            data_range = (data_range[0] + 5, data_range[1] - 5)
            plotter_scaling = (plotter_yrange[1] - plotter_yrange[0]) / float(data_range[1] - data_range[0])
            background.stimulus().present()
            plotter_thread.clear_area()
        elif key == misc.constants.K_UP:
            data_range = (data_range[0] + 5, data_range[1] + 5)
            background.stimulus().present()
            plotter_thread.clear_area()
        elif key == misc.constants.K_DOWN:
            data_range = (data_range[0] - 5, data_range[1] - 5)
            background.stimulus().present()
            plotter_thread.clear_area()

        # process udp
        udp = recorder.process_udp_events()
        while len(udp)>0:
            udp_event = udp.pop(0)

            #remote control
            if remote_control and \
                    udp_event.string.startswith(RcCmd.COMMAND_STR):
                set_marker = False
                if udp_event.string == RcCmd.START:
                    pause_recording = False
                elif udp_event.string == RcCmd.PAUSE:
                    pause_recording = True
                elif udp_event.string == RcCmd.QUIT:
                    quit_recording = True
                elif udp_event.string.startswith(RcCmd.THRESHOLDS):
                    try:
                        threshold = loads[len(RcCmd.THRESHOLDS):]
                    except:
                        threshold = None
                    if not isinstance(threshold, Thresholds): # ensure not strange type
                        threshold = None

                elif udp_event.string == RcCmd.GET_FX:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fx))
                elif udp_event.string == RcCmd.GET_FY:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fy))
                elif udp_event.string == RcCmd.GET_FZ:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fz))
                elif udp_event.string == RcCmd.GET_TX:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fx))
                elif udp_event.string == RcCmd.GET_TY:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fy))
                elif udp_event.string == RcCmd.GET_TZ:
                    recorder.udp.send_queue.put(RcCmd.DATA_POINT +
                                                dumps(sensor_process.Fz))
            else:
                # not remote control command
                set_marker = True
                last_udp_data = udp_event.string


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
        if last_processed_smpl <= sensor_process.sample_cnt:
            # new sample
            smpl = [sensor_process.Fx, sensor_process.Fy, sensor_process.Fz]
            last_processed_smpl = sensor_process.sample_cnt

            if threshold is not None:
                # threshold detection
                history.update([ smpl[level_detection_parameter] ]) # TODO: single sensor only

                tmp, level_change = threshold.get_level(history.moving_average)
                if level_change:
                        recorder.udp.send_queue.put(RcCmd.THRESHOLD_LEVEL+ dumps(tmp))


        #plotting
        if not pause_recording and gui_clock.stopwatch_time >= refresh_interval: #do not give priority to visual output
            gui_clock.reset_stopwatch()

            update_rects = []
            if plot_indicator:
                if plotter_thread is not None:
                    plotter_thread.stop()
                    plotter_thread = None

                ## indicator
                force_data_array = [sensor_process.Fx, sensor_process.Fy, sensor_process.Fz,
                                    sensor_process.Tx, sensor_process.Ty, sensor_process.Tz]
                for cnt in range(6):
                    x_pos = (-3 * indicator_grid) + (cnt * indicator_grid) + 0.5*indicator_grid
                    li = level_indicator(value=force_data_array[cnt],
                                         text=ForceData.forces_names[cnt],
                                         minVal=data_range[0],
                                         maxVal=data_range[1],
                                         width = 50,
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
                txt = stimuli.TextLine(position=pos, text = str(data_range[0]),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                pos = (-220, 145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position= pos, text = str(data_range[1]),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                # end indicator
            else:
                # plotter
                if plotter_thread is None:
                    plotter_thread = PlotterThread(
                        n_data_rows=3,
                        data_row_colours=colours[:3],
                        y_range = plotter_yrange,
                        width=plotter_width,
                        position=plotter_position,
                        background_colour=[10,10,10],
                        axis_colour=misc.constants.C_YELLOW,
                        plot_axis=False)
                    plotter_thread.start()

                if smpl is not None: # newsample
                    plotter_thread.add_values(
                        values = (np.array(smpl, dtype=float)
                                 - (data_range[0] + data_range[1])/2.0) * plotter_scaling,
                        set_marker=set_marker)
                    set_marker = False

                update_rects.append(
                    plotter_thread.get_plotter_rect(exp.screen.size))

                # axis labels
                axis_labels = (int(data_range[0]), int(data_range[1]), 0)
                xpos = plotter_position[0] - (plotter_width/2) - 20
                for cnt, ypos in enumerate((plotter_position[1] + plotter_yrange[0]+10,
                                            plotter_position[1] + plotter_yrange[1]-10,
                                            plotter_position[1] - plotter_scaling*(data_range[0] + data_range[1])/2.0)):
                    stimuli.Canvas(position=(xpos, ypos), size=(50, 30),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                    txt = stimuli.TextLine(position = (xpos, ypos),
                                text = str(axis_labels[cnt]),
                                text_size=15, text_colour=misc.constants.C_YELLOW)
                    txt.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(txt, exp.screen.size))


            # counter
            pos = (-230, 250)
            stimuli.Canvas(position=pos, size=(400,50),
                           colour=misc.constants.C_BLACK).present(
                                    update=False, clear=False)
            txt = stimuli.TextBox(position= pos,
                                size = (400, 50),
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

            # counter
            pos = (200, 250)
            stimuli.Canvas(position=pos, size=(400,50),
                           colour=misc.constants.C_BLUE).present(
                                    update=False, clear=False)
            txt = stimuli.TextBox(position= pos,
                                size = (400, 50),
                                #background_colour=(30,30,30),
                                text_size=15,
                                text = "thresholds: {0}\n".format(
                                                    sensor_process.sample_cnt) +
                                       "n samples buffered: {0} ({1} seconds)".format(
                                    sensor_process.buffer_size,
                                    (gui_clock.time - start_recording_time)/1000),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # last_udp input
            if last_udp_data is not None:
                pos = (420, 250)
                stimuli.Canvas(position=pos, size=(200, 30),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextBox(position= pos, size = (200, 30),
                                    #background_colour=(30,30,30),
                                    text_size=15,
                                    text = "UDP:" + str(last_udp_data),
                                    text_colour=misc.constants.C_YELLOW,
                                    text_justification = 0)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))

            pygame.display.update(update_rects)
            # end refesh screen

        # end while recording

    background.stimulus("Quitting").present()
    if plotter_thread is not None:
        plotter_thread.stop()
    recorder.pause_recording()

def start(remote_control, ask_filename, calibration_file):
    """start gui
    remote_control should be None (ask) or True or False

    """

    # expyriment
    control.defaults.initialize_delay = 0
    control.defaults.pause_key = None
    control.defaults.window_mode = True
    control.defaults.window_size = (1000, 700)
    control.defaults.fast_quit = True
    control.defaults.open_gl = False
    control.defaults.event_logging = 0
    exp = design.Experiment(text_font="freemono")
    exp.set_log_level(0)

    SENSOR_ID = 1  # i.e., NI-device id
    filename = "output.csv"
    timer = Timer()
    sensor1 = SensorSettings(device_id=SENSOR_ID, sync_timer=timer,
                                    calibration_file=calibration_file)

    remote_control = _initialize(exp, remote_control=remote_control)

    recorder = DataRecorder([sensor1], timer=timer,
                            poll_udp_connection=True)

    stimuli.TextLine("Press key to determine bias").present()
    exp.keyboard.wait()
    stimuli.BlankScreen().present()
    recorder.determine_biases(n_samples=500)

    if remote_control:
        stimuli.TextScreen("Waiting to connect with peer",
                           "My IP: " +  recorder.udp.ip_address).present()
        while not recorder.udp.event_is_connected.is_set():
            exp.keyboard.check()
            sleep(0.01)#

        if ask_filename:
            stimuli.TextLine("Wait for filename").present()
            while True:
                try:
                    x = recorder.udp.receive_queue.get_nowait()
                    x = x.string
                except:
                    x = None
                if x is not None and x.startswith(RcCmd.FILENAME):
                    filename = x.replace(RcCmd.FILENAME, "")
                    break
                exp.keyboard.check()
                sleep(0.01)
    else:
        if ask_filename:
            bkg = logo_text_line("")
            filename = io.TextInput("Filename", background_stimulus=bkg).get()
            filename = filename.replace(" ", "_")


    recorder.open_data_file(filename, directory="data", zipped=False,
                        time_stamp_filename=False, comment_line="")

    _record_data(exp, recorder=recorder,
                    plot_indicator = True,
                    remote_control=remote_control)

    recorder.quit()
