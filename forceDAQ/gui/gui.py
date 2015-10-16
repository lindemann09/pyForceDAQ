"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

from time import sleep
import pygame
from cPickle import dumps, loads
import numpy as np

from expyriment import control, design, stimuli, io, misc
from forceDAQ import Thresholds, ForceData, GUIRemoteControlCommands as RcCmd
from forceDAQ.timer import Timer
from forceDAQ.sensor_history import SensorHistory
from forceDAQ.data_recorder import DataRecorder, SensorSettings
from plotter import PlotterThread, level_indicator, Scaling
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

    refresh_interval_plotter = 10
    refresh_interval_indicator = 300
    refresh_interval = refresh_interval_indicator
    indicator_grid = 70  # distance between indicator center

    scaling = Scaling(min_data =-50, max_data = 10,
                      min_plotter_px=-250, max_plotter_px=250)
    plotter_width = 900
    plotter_position = (0, -30)
    plot_filtered = True
    pause_recording = True
    last_recording_status = None
    last_udp_data = None
    current_level = None
    set_marker = False
    clear_screen = False

    gui_clock = misc.Clock()
    background = RecordingScreen(window_size = exp.screen.size,
                                           filename=recorder.filename,
                                           remote_control=remote_control)
    # plotter
    last_processed_smpl = 0
    smpl = None
    plotter_thread = None

    exp.keyboard.clear()

    # TODO one sensor only (Fz), parameter for level detection
    level_detection_parameter = ForceData.forces_names.index("Fz")
    sensor_process = recorder._force_sensor_processes[0]
    history = SensorHistory(history_size = 5, number_of_parameter=3)
    thresholds = None
    quit_recording = False
    while not quit_recording:

        if pause_recording:
            sleep(0.01)

        # process keyboard
        key = exp.keyboard.check(check_for_control_keys=False)
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            quit_recording = True
        elif key == misc.constants.K_v:
            plot_indicator = not(plot_indicator)
            background.stimulus().present()
            if plot_indicator:
                refresh_interval = refresh_interval_indicator
            else:
                refresh_interval = refresh_interval_plotter

        elif key == misc.constants.K_p:
            # pause
            pause_recording = not pause_recording
        elif key == misc.constants.K_KP_MINUS:
            scaling.increase_data_range()
            background.stimulus().present()
            clear_screen = True
        elif key == misc.constants.K_KP_PLUS:
            scaling.decrease_data_range()
            background.stimulus().present()
            clear_screen = True
        elif key == misc.constants.K_UP:
            scaling.data_range_up()
            background.stimulus().present()
            clear_screen = True
        elif key == misc.constants.K_DOWN:
            scaling.data_range_down()
            background.stimulus().present()
            clear_screen = True
        elif key == misc.constants.K_f:
            plot_filtered = not(plot_filtered)

        elif key == misc.constants.K_t:
            tmp = _text2number_array(
                        io.TextInput("Enter thresholds",
                                    background_stimulus=logo_text_line("")).get())
            background.stimulus().present()
            if tmp is not None:
                thresholds = Thresholds(tmp)
            else:
                thresholds = None

            if plotter_thread is not None:
                if thresholds is not None:
                    plotter_thread.set_horizontal_lines(
                            y_values = scaling.data2pxiel(np.array(thresholds.thresholds)))
                else:
                    plotter_thread.set_horizontal_lines(y_values=None)


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
                elif udp_event.string.startswith(RcCmd.SET_THRESHOLDS):
                    try:
                        thresholds = loads[len(RcCmd.SET_THRESHOLDS):]
                    except:
                        thresholds = None
                    if not isinstance(thresholds, Thresholds): # ensure not strange type
                        thresholds = None

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
            history.update(smpl ) # TODO: single sensor only

            if thresholds is not None:
                # threshold detection
                current_level, level_change = thresholds.get_level(history.moving_average[level_detection_parameter])
                if level_change:
                        recorder.udp.send_queue.put(RcCmd.GET_THRESHOLD_LEVEL+ dumps(current_level))

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
                                         scaling=scaling,
                                         width = 50,
                                         position=(x_pos,0),
                                         thresholds=thresholds)
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
                txt = stimuli.TextLine(position=pos, text = str(scaling.min_data),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                pos = (-220, 145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position= pos, text = str(scaling.max_data),
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
                        y_range = [scaling.min_plotter_px, scaling.max_plotter_px],
                        width=plotter_width,
                        position=plotter_position,
                        background_colour=[10,10,10],
                        axis_colour=misc.constants.C_YELLOW,
                        plot_axis=False)
                    plotter_thread.start()
                    if thresholds is not None:
                        plotter_thread.set_horizontal_lines(
                            y_values = scaling.data2pxiel(np.array(thresholds.thresholds)))

                if clear_screen:
                    plotter_thread.clear_area()
                    clear_screen = False

                if smpl is not None: # newsample
                    if plot_filtered:
                        tmp = np.array(history.moving_average, dtype=float)
                    else:
                        tmp = np.array(smpl, dtype=float)

                    plotter_thread.add_values(
                        values = scaling.data2pxiel(tmp),
                        set_marker=set_marker)
                    set_marker = False

                update_rects.append(plotter_thread.get_plotter_rect(exp.screen.size))

                # axis labels
                axis_labels = (int(scaling.min_data), int(scaling.max_data), 0)
                xpos = plotter_position[0] - (plotter_width/2) - 20
                for cnt, ypos in enumerate((plotter_position[1] + scaling.min_plotter_px+10,
                                            plotter_position[1] + scaling.max_plotter_px-10,
                                            scaling.data2pxiel(plotter_position[1]))):
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

            # Infos
            pos = (200, 250)
            tmp = stimuli.Canvas(position=pos, size=(400,50),
                                 colour=misc.constants.C_BLACK)
            tmp.present(update=False, clear=False)
            if thresholds is not None:
                txt = stimuli.TextBox(position= pos,
                                size = (400, 50),
                                text_size = 15,
                                text = "T: {0} L: {1}".format(thresholds,
                                                              current_level),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)

                txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))

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


#### helper
def _text2number_array(txt):
    """helper function"""
    rtn = []
    try:
        for x in txt.split(","):
            rtn.append(float(x))
        return rtn
    except:
        return None