__author__ = "Oliver Lindemann"

try:
    from cPickle import dumps, loads
except: #Python3
    from pickle import dumps, loads

from expyriment import io, misc

from .. import __version__ as forceDAQVersion
from .._lib.misc import SensorHistory
from .._lib.sensor_process import SensorProcess
from .._lib.types import ForceData, Thresholds, GUIRemoteControlCommands as RcCmd

from . import settings
from ._scaling import Scaling
from ._layout import logo_text_line, RecordingScreen

def _text2number_array(txt):
    """helper function"""
    rtn = []
    try:
        for x in txt.split(","):
            rtn.append(float(x))
        return rtn
    except:
        return None

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
            self.history.append( SensorHistory(history_size = settings.gui.moving_average_size,
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

        self.sensor_info_str = ""
        for tmp in self.recorder.sensor_settings_list:
            self.sensor_info_str = self.sensor_info_str + \
                                   "{0}: {1}\n".format(tmp.device_name, tmp.sensor_name)
        self.sensor_info_str = self.sensor_info_str.strip()
        self.plot_indicator = True
        self.plot_filtered = False
        if self.n_sensors == 1:
            self.plot_data_indicator = settings.gui.plot_data_indicator_for_single_sensor
            self.plot_data_plotter = settings.gui.plot_data_plotter_for_single_sensor
        else:
            self.plot_data_indicator = settings.gui.plot_data_indicator_for_two_sensors
            self.plot_data_plotter = settings.gui.plot_data_plotter_for_two_sensors
        # plot data parameter names
        self.plot_data_indicator_names = []
        for x in self.plot_data_indicator:
            self.plot_data_indicator_names.append(self.recorder.sensor_settings_list[x[0]].device_name +\
                                                  "_" + ForceData.forces_names[ x[1]])


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
            tmp = _text2number_array(
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
            if udp_event.byte_string == RcCmd.START:
                self.pause_recording = False
            elif udp_event.byte_string == RcCmd.PAUSE:
                self.pause_recording = True
            elif udp_event.byte_string == RcCmd.QUIT:
                self.quit_recording = True

            elif udp_event.startswith(RcCmd.SET_THRESHOLDS): # thresholds
                try:
                    self.thresholds = loads(
                        udp_event.byte_string[len(RcCmd.SET_THRESHOLDS):])
                    if not isinstance(self.thresholds, Thresholds): # ensure not strange types
                        self.thresholds = None
                    else:
                        self.thresholds.set_number_of_channels(self.n_sensors)
                except:
                    self.thresholds = None

            elif udp_event.startswith(RcCmd.GET_THRESHOLD_LEVEL) or \
                 udp_event.startswith(RcCmd.GET_THRESHOLD_LEVEL2):
                if self.thresholds is not None:
                    s = int(udp_event.startswith(RcCmd.GET_THRESHOLD_LEVEL2))
                    tmp = self.thresholds.get_level(self.level_detection_parameter_average(s))
                    self.recorder.udp.send_queue.put(RcCmd.VALUE + dumps(tmp))
                else:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE + dumps(None))
            elif udp_event.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION) or \
                 udp_event.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2):
                if self.thresholds is not None:
                    s = int(udp_event.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2))
                    self.thresholds.set_level_change_detection(self.level_detection_parameter_average(s),
                                                               channel=s)

            elif udp_event.startswith(RcCmd.SET_RESPONSE_MINMAX_DETECTION) or \
                    udp_event.startswith(RcCmd.SET_RESPONSE_MINMAX_DETECTION2):
                try:
                    duration =  int(loads(
                        udp_event.byte_string[len(RcCmd.SET_RESPONSE_MINMAX_DETECTION):]))
                except:
                    duration = None

                s = int(udp_event.startswith(RcCmd.SET_LEVEL_CHANGE_DETECTION2))
                if self.thresholds is not None and duration is not None:
                    self.thresholds.set_response_minmax_detection(
                        value = self.level_detection_parameter_average(s), duration = duration,
                        channel=s)

            elif udp_event.byte_string == RcCmd.GET_VERSION:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                            dumps(forceDAQVersion))
            elif udp_event.byte_string == RcCmd.PING:
                self.recorder.udp.send_queue.put(RcCmd.PING)
            elif udp_event.byte_string == RcCmd.GET_FX1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fx))
            elif udp_event.byte_string == RcCmd.GET_FY1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fy))
            elif udp_event.byte_string == RcCmd.GET_FZ1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fz))
            elif udp_event.byte_string == RcCmd.GET_TX1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fx))
            elif udp_event.byte_string == RcCmd.GET_TY1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fy))
            elif udp_event.byte_string == RcCmd.GET_TZ1:
                self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                 dumps(self.sensor_processes[0].Fz))
            elif self.n_sensors > 1:
                if udp_event.byte_string == RcCmd.GET_FX2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fx))
                elif udp_event.byte_string == RcCmd.GET_FY2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fy))
                elif udp_event.byte_string == RcCmd.GET_FZ2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fz))
                elif udp_event.byte_string == RcCmd.GET_TX2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fx))
                elif udp_event.byte_string == RcCmd.GET_TY2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fy))
                elif udp_event.byte_string == RcCmd.GET_TZ2:
                    self.recorder.udp.send_queue.put(RcCmd.VALUE +
                                                     dumps(self.sensor_processes[1].Fz))
        else:
            # not remote control command
            self.set_marker = True
            self.last_udp_data = udp_event.byte_string


    def update_history(self, sensor):
        self.history[sensor].update(self.sensor_processes[sensor].get_Fxyz())

    def level_detection_parameter_average(self, sensor):
        """just a short cut"""
        if sensor < self.n_sensors:
            return self.history[sensor].moving_average[self.level_detection_parameter]
        else:
            return None


