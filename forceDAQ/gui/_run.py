"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import pygame
try:
    from cPickle import dumps, loads
except: #Python3
    from pickle import dumps, loads

import numpy as np
from expyriment import control, design, stimuli, io, misc
import logging

from .. import __version__ as forceDAQVersion
from .._lib.data_recorder import DataRecorder, SensorSettings
from .._lib.sensor_process import SensorProcess
from .._lib.types import ForceData, GUIRemoteControlCommands as RcCmd
from .._lib.timer import app_timer

from . import settings
from ._plotter import PlotterThread
from ._level_indicator import level_indicator
from ._layout import logo_text_line, colours, get_pygame_rect
from ._gui_status import GUIStatus

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

def _main_loop(exp, recorder, remote_control=False):
    """udp command:
            "start", "pause", "stop"
            "thresholds = [x,...]" : start level detection for Fz parameter and set threshold
            "thresholds stop" : stop level detection
    """

    indicator_grid = 70  # distance between indicator center
    plotter_width = 900
    plotter_position = (0, -30)

    s = GUIStatus(screen_refresh_interval_indicator = settings.gui.screen_refresh_interval_indicator,
                  screen_refresh_interval_plotter = settings.gui.gui_screen_refresh_interval_plotter,
                  recorder = recorder,
                  remote_control=remote_control,
                  level_detection_parameter = ForceData.forces_names.index(
                                                        settings.gui.level_detection_parameter),  # only one dimension
                  screen_size = exp.screen.size,
                  data_min_max=settings.gui.data_min_max,
                  plotter_pixel_min_max=settings.gui.plotter_pixel_min_max,
                  indicator_pixel_min_max=settings.gui.indicator_pixel_min_max,
                  plot_axis = settings.gui.plot_axis)

    # plotter
    plotter_thread = None
    exp.keyboard.clear()

    while not s.quit_recording:  ######## process loop
        if s.pause_recording:
            app_timer.wait(100)

        ################################ process keyboard
        s.process_key(exp.keyboard.check(check_for_control_keys=False))

        ##############################  process udp
        udp = recorder.process_and_write_udp_events()
        while len(udp)>0:
            s.process_udp_event(udp.pop(0))

        ########################### process new samples
        for x in s.check_new_samples():
            s.update_history(sensor=x)

            if s.thresholds is not None:
                # level change detection
                level_change, tmp = s.thresholds.get_level_change(
                                                s.history[x].moving_average[s.level_detection_parameter],
                                                channel=x)
                if level_change:
                    if x==1:
                        recorder.udp.send_queue.put(RcCmd.CHANGED_LEVEL2+ dumps(tmp))
                    else:
                        recorder.udp.send_queue.put(RcCmd.CHANGED_LEVEL+ dumps(tmp))

                # minmax detection
                tmp = s.thresholds.get_response_minmax(
                                                s.history[x].moving_average[s.level_detection_parameter],
                                                channel=x)
                if tmp is not None:
                    if x==1:
                        recorder.udp.send_queue.put(RcCmd.RESPONSE_MINMAX2 + dumps(tmp))
                    else:
                        recorder.udp.send_queue.put(RcCmd.RESPONSE_MINMAX + dumps(tmp))


        ######################## show pause or recording screen
        if s.check_recording_status_change():
            if plotter_thread is not None:
                plotter_thread.join()
                plotter_thread = None

            if s.pause_recording:
                recorder.pause_recording(s.background)
                s.background.stimulus("Paused ('b' for baseline)").present()
                if remote_control:
                    recorder.udp.send_queue.put(RcCmd.FEEDBACK_PAUSED)
            else:
                recorder.start_recording()
                s.set_start_recording_time()
                s.background.stimulus().present()
                if remote_control:
                    recorder.udp.send_queue.put(RcCmd.FEEDBACK_STARTED)

        ###########################
        ########################### plotting
        ###########################

        if s.check_refresh_required(): #do not give priority to visual output
            update_rects = []

            if s.check_thresholds_changed():
                _draw_plotter_thread_thresholds(plotter_thread, s.thresholds, s.scaling_plotter)

            if s.plot_indicator:
                ############################################  plot_indicator
                if plotter_thread is not None:
                    plotter_thread.join()
                    plotter_thread = None

                ## indicator
                force_data_array = list(map(lambda x: s.sensor_processes[x[
                    0]].get_force(x[1]), s.plot_data_indicator))

                for cnt in range(6):
                    x_pos = (-3 * indicator_grid) + (cnt * indicator_grid) + 0.5*indicator_grid

                    if cnt == s.level_detection_parameter:
                        thr = s.thresholds
                    else:
                        thr = None
                    li = level_indicator(value=force_data_array[cnt],
                                         text=s.plot_data_indicator_names[cnt],
                                         scaling=s.scaling_indicator,
                                         width = 50,
                                         position=(x_pos,0),
                                         thresholds=thr)
                    li.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(li, exp.screen.size))


                #line
                zero = s.scaling_indicator.data2pixel(s.scaling_indicator.trim(0))
                rect = stimuli.Line(start_point=(-200,zero), end_point=(200,zero),
                                    line_width=1, colour=misc.constants.C_YELLOW)
                rect.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(rect, exp.screen.size))

                # axis labels
                pos = (-220, -145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position=pos, text = str(s.scaling_indicator.min),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                pos = (-220, 145)
                stimuli.Canvas(position=pos, size=(30,20),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextLine(position= pos, text = str(s.scaling_indicator.max),
                            text_size=15, text_colour=misc.constants.C_YELLOW)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                # end indicator

                stimuli.Canvas(position=(-250, 200), size=(200, 50),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextBox(text = str(s.sensor_info_str),
                                      #background_colour=(30,30,30),
                                size=(200, 50),
                                text_size=15,
                                position=(-250, 200),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
            else:
                ############################################  plotter
                if plotter_thread is None:
                    plotter_thread = PlotterThread(
                        n_data_rows= len(s.plot_data_plotter),
                        data_row_colours=colours[:len(s.plot_data_plotter)],
                        y_range = [s.scaling_plotter.pixel_min, s.scaling_plotter.pixel_max],
                        width=plotter_width,
                        position=plotter_position,
                        background_colour=[10, 10, 10],
                        axis_colour=misc.constants.C_YELLOW)
                    plotter_thread.start()

                    if s.plot_axis:
                        plotter_thread.set_horizontal_lines(
                            y_values = [s.scaling_plotter.data2pixel(0)])

                    if s.thresholds is not None:
                        plotter_thread.set_horizontal_lines(
                            y_values = s.scaling_plotter.data2pixel(
                                np.array(s.thresholds.thresholds)))

                if s.clear_screen:
                    plotter_thread.clear_area()
                    s.clear_screen = False

                if s.plot_filtered:
                    tmp = np.array(list(map(lambda x: s.history[x[
                        0]].moving_average[x[1]], s.plot_data_plotter)),
                                   dtype=float)
                else:
                    tmp = np.array(list(map(lambda x: s.sensor_processes[x[
                        0]].get_force(x[1]), s.plot_data_plotter)),
                                   dtype=float)

                if s.thresholds is not None:
                    point_marker = s.thresholds.is_detecting_anything()
                else:
                    point_marker = False

                plotter_thread.add_values(
                    values = s.scaling_plotter.data2pixel(tmp),
                    set_marker=s.set_marker,
                    set_point_marker=point_marker)
                s.set_marker = False

                update_rects.append(plotter_thread.get_plotter_rect(exp.screen.size))

                # axis labels
                axis_labels = (int(s.scaling_plotter.min), int(s.scaling_plotter.max), 0)
                xpos = plotter_position[0] - (plotter_width/2) - 20
                for cnt, ypos in enumerate((plotter_position[1] + s.scaling_plotter.pixel_min + 10,
                                            plotter_position[1] + s.scaling_plotter.pixel_max - 10,
                                            plotter_position[1] + s.scaling_plotter.data2pixel(0))):
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
                                text = "n samples (total): {0}\nn samples: {1} ({2} sec.)".format(
                                    str(list(map(SensorProcess.get_sample_cnt,
                                             s.sensor_processes)))[1:-1],
                                    str(list(map(SensorProcess.get_buffer_size,
                                             s.sensor_processes)))[1:-1],
                                    s.recording_duration_in_sec),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # Infos
            pos = (200, 250)
            tmp = stimuli.Canvas(position=pos, size=(400,50),
                                 colour=misc.constants.C_BLACK)
            tmp.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))
            if s.thresholds is not None:
                if s.n_sensors>1:
                    tmp = [s.thresholds.get_level(s.level_detection_parameter_average(0)),
                           s.thresholds.get_level(s.level_detection_parameter_average(1))]
                else:
                    tmp = s.thresholds.get_level(s.level_detection_parameter_average(0))
                txt = stimuli.TextBox(position= pos,
                                size = (400, 50),
                                text_size = 15,
                                text = "T: {0} L: {1}".format(s.thresholds, tmp),
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)

                txt.present(update=False, clear=False)

            pos = (400, 250)
            tmp = stimuli.Canvas(position=pos, size=(400,50),
                                 colour=misc.constants.C_BLACK)
            tmp.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))
            if s.plot_filtered:
                txt = stimuli.TextBox(position= pos,
                                size = (400, 50),
                                text_size = 15,
                                text = "Filtered data!",
                                text_colour=misc.constants.C_YELLOW,
                                text_justification = 0)
                txt.present(update=False, clear=False)

            # last_udp input
            if s.last_udp_data is not None:
                pos = (420, 250)
                stimuli.Canvas(position=pos, size=(200, 30),
                               colour=misc.constants.C_BLACK).present(
                                        update=False, clear=False)
                txt = stimuli.TextBox(position= pos, size = (200, 30),
                                    #background_colour=(30,30,30),
                                    text_size=15,
                                    text = "UDP:" + str(s.last_udp_data),
                                    text_colour=misc.constants.C_YELLOW,
                                    text_justification = 0)
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))

            pygame.display.update(update_rects)
            # end plotting screen

        ##### end main  loop

    s.background.stimulus("Quitting").present()
    if plotter_thread is not None:
        plotter_thread.join()
    recorder.pause_recording(s.background)


def run():

    return run_with_options(remote_control = settings.recording.remote_control,
                            ask_filename = settings.recording.ask_filename,
                            device_ids = settings.recording.device_ids,
                            sensor_names = settings.recording.sensor_names,
                            calibration_folder = settings.recording.calibration_folder,
                            device_name_prefix = settings.recording.device_name_prefix,
                            write_Fx = settings.recording.write_Fx,
                            write_Fy = settings.recording.write_Fy,
                            write_Fz = settings.recording.write_Fz,
                            write_Tx = settings.recording.write_Tx,
                            write_Ty = settings.recording.write_Ty,
                            write_Tz = settings.recording.write_Tz,
                            write_trigger1 = settings.recording.write_trigger1,
                            write_trigger2 = settings.recording.write_trigger2,
                            zip_data=settings.recording.zip_data,
                            reverse_scaling = settings.recording.reverse_scaling,
                            convert_to_forces=settings.recording.convert_to_forces,
                            polling_priority=settings.recording.priority)

def run_with_options(remote_control,
                     ask_filename,
                     device_ids,
                     sensor_names,
                     calibration_folder,
                     device_name_prefix="Dev",
                     write_Fx = True,
                     write_Fy = True,
                     write_Fz = True,
                     write_Tx = False,
                     write_Ty = False,
                     write_Tz = False,
                     write_trigger1 = True,
                     write_trigger2 = False,
                     zip_data=False,
                     reverse_scaling = None,
                     convert_to_forces = True,
                     polling_priority=None):

    """start gui
    remote_control should be None (ask) or True or False

    reverse scaling: dictionary with rescaling (see SensorSetting)
                key: device_id, value: list of parameter names (e.g., ["Fx"])

   polling_priority has to be types.PRIORITY_{HIGH}, {REALTIME} or
                        {NORMAL} or None

    returns False only if quited by key while waiting for remote control
    """
    #

    logging.info("New Recording with forceDAQ {}".format(forceDAQVersion))
    logging.info("Sensors {}".format(sensor_names))

    if not isinstance(device_ids, (list, tuple)):
        device_ids = [device_ids]
    if not isinstance(sensor_names, (list, tuple)):
        sensor_names = [sensor_names]

    sensors = []
    for d_id, sn in zip(device_ids, sensor_names):
        try:
            reverse_parameter_names = reverse_scaling[str(d_id)]
        except:
            reverse_parameter_names = []

        sensors.append(SensorSettings(device_id = d_id,
                                      device_name_prefix=device_name_prefix,
                                      sensor_name = sn,
                                      calibration_folder=calibration_folder,
                                      reverse_parameter_names=reverse_parameter_names,
                                      rate = settings.gui.sampling_rate,
                                      convert_to_FT=convert_to_forces))



    # expyriment
    control.defaults.initialize_delay = 0
    control.defaults.pause_key = None
    control.defaults.window_mode = True
    control.defaults.window_size = (1000, 700)
    control.defaults.fast_quit = True
    control.defaults.open_gl = False
    control.defaults.event_logging = 0
    control.defaults.audiosystem_autostart = False
    exp = design.Experiment(text_font=settings.gui.window_font)
    exp.set_log_level(0)


    filename = "output.csv"
    remote_control = _initialize(exp, remote_control=remote_control)
    logo_text_line("Initializing Force Recording").present()

    recorder = DataRecorder(sensors,
                 poll_udp_connection=True,
                 write_deviceid = len(device_ids)>1,
                 write_Fx = write_Fx,
                 write_Fy = write_Fy,
                 write_Fz = write_Fz,
                 write_Tx = write_Tx,
                 write_Ty = write_Ty,
                 write_Tz = write_Tz,
                 write_trigger1= write_trigger1,
                 write_trigger2= write_trigger2,
                 polling_priority=polling_priority)

    app_timer.wait(200) # wait for lib init
    recorder.determine_biases(n_samples=500)


    if remote_control:
        logo_text_line("Waiting to connect (my IP: {0})".format(
                    recorder.udp.my_ip)).present()
        while not recorder.udp.event_is_connected.is_set():
            key = exp.keyboard.check(check_for_control_keys=False)
            if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
                recorder.quit()
                control.end()
                return False
            app_timer.wait(100)

        logo_text_line("Wait for filename").present()
        while True:
            try:
                x = recorder.udp.receive_queue.get_nowait()
            except:
                x = None

            if x is not None and x.startswith(RcCmd.FILENAME):
                filename = x.byte_string[len(RcCmd.FILENAME):].decode('utf-8', 'replace')
                break
            exp.keyboard.check()
            app_timer.wait(100)
    else:
        if ask_filename:
            bkg = logo_text_line("")
            filename = io.TextInput("Filename", background_stimulus=bkg).get()
            filename = filename.replace(" ", "_")


    recorder.open_data_file(filename,
                            subdirectory="data",
                            zipped=zip_data,
                            time_stamp_filename=False,
                            comment_line="")

    _main_loop(exp, recorder=recorder,
               remote_control=remote_control)

    recorder.quit()
    control.end()
    return True


#### helper
def _draw_plotter_thread_thresholds(plotter_thread, thresholds, scaling):
    if plotter_thread is not None:
        if thresholds is not None:
            plotter_thread.set_horizontal_lines(
                    y_values = scaling.data2pixel(np.array(thresholds.thresholds)))
        else:
            plotter_thread.set_horizontal_lines(y_values=None)


def _strlist_append(prefix, strlist):
    return list(map(lambda x: prefix+x, strlist))
