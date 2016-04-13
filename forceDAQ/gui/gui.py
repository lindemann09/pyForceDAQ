"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import os
import pygame
from cPickle import dumps, loads
from time import sleep

import numpy as np
from expyriment import control, design, stimuli, io, misc

from . import config
from layout import logo_text_line, colours, get_pygame_rect, RecordingScreen
from plotter import PlotterThread, level_indicator, Scaling
from .. import __version__ as forceDAQVersion
from ..base.data_recorder import DataRecorder, SensorSettings
from ..base.forceDAQ_types import ForceData,  Thresholds, GUIRemoteControlCommands as RcCmd
from ..base.sensor_history import SensorHistory
from ..base.timer import Timer
from ..daq.sensor import SensorProcess

def initialize(exp, remote_control=None):
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

class GUIStatus(object):

    def __init__(self,
                 screen_refresh_interval_indicator,
                 screen_refresh_interval_plotter,
                 recorder,
                 remote_control,
                 level_detection_parameter,
                 data_min_max,
                 plotter_pixel_min_max,
                 indicator_pixel_min_max,
                 screen_size,
                 plot_axis):

        self.screen_refresh_interval_indicator = screen_refresh_interval_indicator
        self.screen_refresh_interval_plotter = screen_refresh_interval_plotter
        self.plot_axis = plot_axis
        self.recorder = recorder
        self.remote_control = remote_control
        self.level_detection_parameter = level_detection_parameter

        self.background = RecordingScreen(window_size = screen_size,
                                          filename=recorder.filename,
                                          remote_control=remote_control)
        self.scaling_plotter = Scaling(min=data_min_max[0], max= data_min_max[1],
                      pixel_min=plotter_pixel_min_max[0],
                      pixel_max=plotter_pixel_min_max[1])
        self.scaling_indicator = Scaling(min=data_min_max[0], max= data_min_max[1],
                                pixel_min = indicator_pixel_min_max[0],
                                pixel_max = indicator_pixel_min_max[1])


        self.sensor_processes = recorder.force_sensor_processes
        self.n_sensors = len(self.sensor_processes)
        self.history = []
        for _ in range(self.n_sensors):
            self.history.append( SensorHistory(history_size = config.moving_average_size,
                                               number_of_parameter= 3) )

        self._start_recording_time = 0
        self.pause_recording = True
        self.quit_recording = False
        self.clear_screen = True
        self.thresholds = None
        self.set_marker = False
        self.last_udp_data = None
        self._last_processed_smpl = [0] * self.n_sensors
        self._last_recording_status = None
        self._last_thresholds = None
        self._clock = misc.Clock()

        self.plot_indicator = True
        self.plot_filtered = False
        if self.n_sensors == 1:
            self.plot_data_indicator = config.plot_data_indicator_for_single_sensor
            self.plot_data_plotter = config.plot_data_plotter_for_single_sensor
        else:
            self.plot_data_indicator = config.plot_data_indicator_for_two_sensors
            self.plot_data_plotter = config.plot_data_plotter_for_two_sensors
        # plot data parameter names
        self.plot_data_indicator_names = []
        for x in self.plot_data_indicator:
            self.plot_data_indicator_names.append(str(x[0]) + "_" + ForceData.forces_names[ x[1]])
        self.plot_data_plotter_names = []
        for x in self.plot_data_plotter:
            self.plot_data_plotter_names.append(str(x[0]) + "_" + ForceData.forces_names[ x[1]])


    def set_start_recording_time(self):
        self._start_recording_time = self._clock.time

    @property
    def recording_duration_in_sec(self):
        return (self._clock.time - self._start_recording_time) / 1000

    def check_refresh_required(self):
        """also resets clock"""
        if self.plot_indicator:
            intervall = self.screen_refresh_interval_indicator
        else:
            intervall = self.screen_refresh_interval_plotter

        if not self.pause_recording and self._clock.stopwatch_time >= intervall:
            self._clock.reset_stopwatch()
            return True
        return False

    def check_recording_status_change(self):
        """returns only onces true if not changed between calls"""
        if self.pause_recording != self._last_recording_status:
            self._last_recording_status = self.pause_recording
            return True
        return False

    def check_new_samples(self):
        """returns list of sensors with new samples"""
        rtn = []
        for i,cnt in enumerate(map(SensorProcess.get_sample_cnt, self.sensor_processes)):
            if self._last_processed_smpl[i] < cnt:
                # new sample
                self._last_processed_smpl[i] = cnt
                rtn.append(i)
        return rtn

    def check_thresholds_changed(self):
        """returns only true if not changed between calls"""
        if self.thresholds != self._last_thresholds:
            # new sample
            self._last_thresholds = self.thresholds
            return True
        return False

    def process_key(self, key):
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            self.quit_recording = True
        elif key == misc.constants.K_v:
            self.plot_indicator = not self.plot_indicator
            self.background.stimulus().present()

        elif key == misc.constants.K_p:
            # pause
            self.pause_recording = not self.pause_recording
        elif key == misc.constants.K_b and self.pause_recording:
            self.background.stimulus("Recording baseline").present()
            self.recorder.determine_biases(n_samples=500)
            self.background.stimulus("Paused").present()

        elif key == misc.constants.K_KP_MINUS:
            self.scaling_plotter.increase_data_range()
            self.scaling_indicator.increase_data_range()
            self.background.stimulus().present()
            self.clear_screen = True
        elif key == misc.constants.K_KP_PLUS:
            self.scaling_plotter.decrease_data_range()
            self.scaling_indicator.decrease_data_range()
            self.background.stimulus().present()
            self.clear_screen = True
        elif key == misc.constants.K_UP:
            self.scaling_plotter.data_range_up()
            self.scaling_indicator.data_range_up()
            self.background.stimulus().present()
            self.clear_screen = True
        elif key == misc.constants.K_DOWN:
            self.scaling_plotter.data_range_down()
            self.scaling_indicator.data_range_down()
            self.background.stimulus().present()
            self.clear_screen = True
        elif key == misc.constants.K_f:
            self.plot_filtered = not self.plot_filtered

        elif key == misc.constants.K_t:
            tmp = text2number_array(
                        io.TextInput("Enter thresholds",
                                    background_stimulus=logo_text_line("")).get())
            self.background.stimulus().present()
            if tmp is not None:
                self.thresholds = Thresholds(tmp, n_channels=self.n_sensors)
            else:
                self.thresholds = None

    def process_udp_event(self, udp_event):
        """remote control

        See commands in forceDAQ_type.GUIRemoteControlCommands
        """

        if self.remote_control and udp_event.is_remote_control_command:
            if udp_event.string == RcCmd.START:
                self.pause_recording = False
            elif udp_event.string == RcCmd.PAUSE:
                self.pause_recording = True
            elif udp_event.string == RcCmd.QUIT:
                self.quit_recording = True

            elif udp_event.string.startswith(RcCmd.SET_THRESHOLDS): # thresholds
                try:
                    self.thresholds = loads(
                        udp_event.string[len(RcCmd.SET_THRESHOLDS):])
                    if not isinstance(self.thresholds, Thresholds): # ensure not strange types
                        self.thresholds = None
                    else:
                        self.thresholds.set_number_of_channels(self.n_sensors)
                except:
                    self.thresholds = None

            elif udp_event.string.startswith(RcCmd.GET_THRESHOLD_LEVEL) or \
                 udp_event.string.startswith(RcCmd.GET_THRESHOLD_LEVEL2):
                if self.thresholds is not None:
                    s = int(udp_event.string.startswith(RcCmd.GET_THRESHOLD_LEVEL2))
                    tmp = self.thresholds.get_level(self.level_detection_parameter_average(s))
                    self.recorder.udp.send_queue.put(RcCmd.VALUE + dumps(tmp))
                else:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE + dumps(None))
            elif udp_event.string.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION) or \
                 udp_event.string.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2):
                if self.thresholds is not None:
                    s = int(udp_event.string.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2))
                    self.thresholds.set_level_change_detection(self.level_detection_parameter_average(s),
                                                               channel=s)

            elif udp_event.string.startswith(RcCmd.SET_RESPONSE_MINMAX_DETECTION) or \
                    udp_event.string.startswith(RcCmd.SET_RESPONSE_MINMAX_DETECTION2):
                try:
                    duration =  int(loads(
                        udp_event.string[len(RcCmd.SET_RESPONSE_MINMAX_DETECTION):]))
                except:
                    duration = None

                s = int(udp_event.string.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2))
                if self.thresholds is not None and duration is not None:
                    self.thresholds.set_response_minmax_detection(
                        value = self.level_detection_parameter_average(s), duration = duration,
                        channel=s)

            elif udp_event.string == RcCmd.GET_VERSION:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                            dumps(forceDAQVersion))
            elif udp_event.string == RcCmd.PING:
                self.recorder.udp.send_queue.put(RcCmd.PING)
            elif udp_event.string == RcCmd.GET_FX:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fx))
            elif udp_event.string == RcCmd.GET_FY:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fy))
            elif udp_event.string == RcCmd.GET_FZ:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fz))
            elif udp_event.string == RcCmd.GET_TX:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fx))
            elif udp_event.string == RcCmd.GET_TY:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fy))
            elif udp_event.string == RcCmd.GET_TZ:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fz))
            elif self.n_sensors > 1:
                if udp_event.string == RcCmd.GET_FX2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fx))
                elif udp_event.string == RcCmd.GET_FY2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fy))
                elif udp_event.string == RcCmd.GET_FZ2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fz))
                elif udp_event.string == RcCmd.GET_TX2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fx))
                elif udp_event.string == RcCmd.GET_TY2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fy))
                elif udp_event.string == RcCmd.GET_TZ2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fz))
        else:
            # not remote control command
            self.set_marker = True
            self.last_udp_data = udp_event.string


    def update_history(self, sensor):
        self.history[sensor].update(self.sensor_processes[sensor].get_Fxyz())

    def level_detection_parameter_average(self, sensor):
        """just a short cut"""
        if sensor<=self.n_sensors:
            return self.history[sensor].moving_average[self.level_detection_parameter]


def main_loop(exp, recorder, remote_control=False):
    """udp command:
            "start", "pause", "stop"
            "thresholds = [x,...]" : start level detection for Fz parameter and set threshold
            "thresholds stop" : stop level detection
    """

    indicator_grid = 70  # distance between indicator center
    plotter_width = 900
    plotter_position = (0, -30)

    s = GUIStatus(screen_refresh_interval_indicator = config.screen_refresh_interval_indicator,
                  screen_refresh_interval_plotter = config.gui_screen_refresh_interval_plotter,
                  recorder = recorder,
                  remote_control=remote_control,
                  level_detection_parameter = ForceData.forces_names.index(
                                                        config.level_detection_parameter),  # only one dimension
                       screen_size = exp.screen.size,
                  data_min_max=config.data_min_max,
                  plotter_pixel_min_max=config.plotter_pixel_min_max,
                  indicator_pixel_min_max=config.indicator_pixel_min_max,
                  plot_axis = config.plot_axis)

    # plotter
    plotter_thread = None
    exp.keyboard.clear()

    while not s.quit_recording:  ######## process loop
        if s.pause_recording:
            sleep(0.01)

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
            if s.pause_recording:
                s.background.stimulus("writing data...").present()
                recorder.pause_recording()
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
                draw_plotter_thread_thresholds(plotter_thread, s.thresholds, s.scaling_plotter)

            if s.plot_indicator:
                ############################################  plot_indicator
                if plotter_thread is not None:
                    plotter_thread.stop()
                    plotter_thread = None

                ## indicator
                force_data_array = map(lambda x: s.sensor_processes[x[0]].get_force(x[1]), s.plot_data_indicator)

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
                    tmp = np.array(map(lambda x: s.history[x[0]].moving_average[x[1]], s.plot_data_plotter),
                                   dtype=float)
                else:
                    tmp = np.array(map(lambda x: s.sensor_processes[x[0]].get_force(x[1]), s.plot_data_plotter),
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
                                text = "n samples base: {0}\nn samples buffered: {1} ({2} seconds)".format(
                                    str(map(SensorProcess.get_sample_cnt, s.sensor_processes))[1:-1],
                                    str(map(SensorProcess.get_buffer_size, s.sensor_processes))[1:-1],
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
        plotter_thread.stop()
    recorder.pause_recording(s.background)


def logo_text_line(text):
    blank = stimuli.Canvas(size=(600, 400))
    logo = stimuli.Picture(filename=os.path.join(os.path.dirname(__file__),
                            "forceDAQ_logo.png"), position = (0, 150))
    logo.scale(0.6)
    stimuli.TextLine(text="Version " + forceDAQVersion, position=(0,80),
                     text_size = 14,
                     text_colour=misc.constants.C_EXPYRIMENT_ORANGE).plot(blank)
    logo.plot(blank)
    stimuli.TextLine(text=text).plot(blank)
    return blank


def start(remote_control,
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
          reverse_scaling = None):

    """start gui
    remote_control should be None (ask) or True or False

    reverse scaling: dictionary with rescaling (see SensorSetting)
                key: device_id, value: list of parameter names (e.g., ["Fx"])

    returns False only if quited by key while waiting for remote control
    """

    if not isinstance(device_ids, (list, tuple)):
        device_ids = [device_ids]
    if not isinstance(sensor_names, (list, tuple)):
        sensor_names = [sensor_names]
    timer = Timer()
    sensors = []
    for d_id, sn in zip(device_ids, sensor_names):
        try:
            reverse_parameter_names = reverse_scaling[d_id]
        except:
            reverse_parameter_names = []

        sensors.append(SensorSettings(device_id = d_id,
                                      device_name_prefix=device_name_prefix,
                                      sensor_name = sn,
                                      sync_timer=timer,
                                      calibration_folder=calibration_folder,
                                      reverse_parameter_names=reverse_parameter_names))



    # expyriment
    control.defaults.initialize_delay = 0
    control.defaults.pause_key = None
    control.defaults.window_mode = True
    control.defaults.window_size = (1000, 700)
    control.defaults.fast_quit = True
    control.defaults.open_gl = False
    control.defaults.event_logging = 0
    exp = design.Experiment(text_font=config.window_font)
    exp.set_log_level(0)


    filename = "output.csv"
    remote_control = initialize(exp, remote_control=remote_control)
    logo_text_line("Initializing Force Recording").present()

    recorder = DataRecorder(sensors, timer=timer,
                 poll_udp_connection=True,
                 write_deviceid = len(device_ids)>1,
                 write_Fx = write_Fx,
                 write_Fy = write_Fy,
                 write_Fz = write_Fz,
                 write_Tx = write_Tx,
                 write_Ty = write_Ty,
                 write_Tz = write_Tz,
                 write_trigger1= write_trigger1,
                 write_trigger2= write_trigger2)

    sleep(0.2) # wait for base init
    recorder.determine_biases(n_samples=500)

    if remote_control:
        logo_text_line("Waiting to connect (my IP: {0})".format(
                    recorder.udp.ip_address)).present()
        while not recorder.udp.event_is_connected.is_set():
            key = exp.keyboard.check(check_for_control_keys=False)
            if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
                recorder.quit()
                control.end()
                return False
            sleep(0.01)#

        logo_text_line("Wait for filename").present()
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


    recorder.open_data_file(filename,
                            directory="data",
                            zipped=zip_data,
                            time_stamp_filename=False,
                            comment_line="")

    main_loop(exp, recorder=recorder,
              remote_control=remote_control)

    recorder.quit()
    control.end()
    return True


#### helper
def text2number_array(txt):
    """helper function"""
    rtn = []
    try:
        for x in txt.split(","):
            rtn.append(float(x))
        return rtn
    except:
        return None

def draw_plotter_thread_thresholds(plotter_thread, thresholds, scaling):
    if plotter_thread is not None:
        if thresholds is not None:
            plotter_thread.set_horizontal_lines(
                    y_values = scaling.data2pixel(np.array(thresholds.thresholds)))
        else:
            plotter_thread.set_horizontal_lines(y_values=None)


def strlist_append(prefix, strlist):
    return map(lambda x: prefix+x, strlist)