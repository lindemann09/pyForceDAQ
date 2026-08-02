__author__ = "Oliver Lindemann"


from time import sleep

from expyriment import io, misc

from ..lib.data_recorder import DataRecorder
from ..lib.rec_tools import DataBuffer, Thresholds
from ..lib.sensor_process import SensorProcess
from ..lib.settings import GUISettings
from ..lib.types import ForceSensorData
from ._layout import RecordingScreen, expy_constants, logo_text_line
from ._scaling import Scaling


def _text2number_array(txt) -> list[float] | None:
    """helper function"""
    rtn = []
    try:
        for x in txt.split(","):
            rtn.append(float(x))
        return rtn
    except Exception:
        return None


class GUIStatus:

    def __init__(
        self,
        gui_settings: GUISettings,
        recorder: DataRecorder,
        screen_size: tuple[int, int],
        top_left_info:list[str] = [""]
    ):

        self.gs = gui_settings
        self.recorder = recorder
        self.screen_size = screen_size
        self.top_left_info = top_left_info

        self.scaling_plotter = Scaling(
            min=gui_settings.data_min_max[0],
            max=gui_settings.data_min_max[1],
            pixel_min=gui_settings.plotter_pixel_min_max[0],
            pixel_max=gui_settings.plotter_pixel_min_max[1],
        )
        self.scaling_indicator = Scaling(
            min=gui_settings.data_min_max[0],
            max=gui_settings.data_min_max[1],
            pixel_min=gui_settings.indicator_pixel_min_max[0],
            pixel_max=gui_settings.indicator_pixel_min_max[1],
        )

        self.sensor_processes = recorder.force_sensor_processes
        self.n_sensors = len(self.sensor_processes)
        self.force_id_level_detect = ForceSensorData.force_id(gui_settings.level_detection_parameter)

        self.history: list[DataBuffer] = []

        for _ in range(self.n_sensors):
            self.history.append(
                DataBuffer(
                    maxlen=gui_settings.moving_average_size
                )
            )

        self.pause_recording = False
        self.quit_recording = False
        self.clear_screen = True
        self.threshold_list: list[Thresholds] = []
        self.set_marker = False
        self._last_processed_smpl = [0] * self.n_sensors
        self._clock = misc.Clock()

        self.sensor_info_str = ""
        for tmp in self.recorder.sensor_settings_list:
            self.sensor_info_str = self.sensor_info_str + f"{tmp.device_label}\n"
        self.sensor_info_str = self.sensor_info_str.strip()
        self.plot_indicator = True
        if self.n_sensors == 1:
            self.plot_data_indicator = (
                gui_settings.plot_data_indicator_for_single_sensor
            )
            self.plot_data_plotter = gui_settings.plot_data_plotter_for_single_sensor
        else:
            self.plot_data_indicator = gui_settings.plot_data_indicator_for_two_sensors
            self.plot_data_plotter = gui_settings.plot_data_plotter_for_two_sensors
        # plot data parameter names
        self.plot_data_indicator_names = []
        for x in self.plot_data_indicator:
            self.plot_data_indicator_names.append(
                self.recorder.sensor_settings_list[x[0]].device_label
                + "_"
                + ForceSensorData.forces_names[x[1]]
            )

        self.plot_data_plotter_names = []
        for x in self.plot_data_plotter:
            self.plot_data_plotter_names.append(
                str(x[0]) + "_" + ForceSensorData.forces_names[x[1]]
            )

        self.background = self._make_background()

    def _make_background(self, default_text_colour=expy_constants.C_YELLOW) -> RecordingScreen:
        txt_col = default_text_colour

        if self.recorder.recording_settings.lsl_stream:
            info_recording = "LSL STREAM"
            if self.recorder.recording_settings.save_data:
                info_recording += " | "
        else:
            info_recording = ""

        if self.recorder.has_file_writer:
            if self.pause_recording:
                info_recording += "SAVING PAUSED "
                txt_col = expy_constants.C_RED
            else:
                info_recording += "SAVING"
                txt_col = expy_constants.C_GREEN
        if len(info_recording) == 0:
            info_recording = "DATA ARE NOT SAVED OR STREAMED!"
        if self.recorder.has_file_writer:
            info_file = f"file: {self.recorder.file_writer.filepath.name}" # type: ignore
        else:
            if self.recorder.recording_settings.lsl_stream:
                info_file = "no local file"
            else:
                info_file = info_recording

        return RecordingScreen(
            window_size=self.screen_size,
            txt_top_left=self.top_left_info,
            txt_top_right=info_file,
            txt_top_center=info_recording,
            text_colour=txt_col,
            no_pause_option = not self.recorder.has_file_writer
            )

    def check_refresh_required(self):
        """also resets clock"""
        if self.plot_indicator:
            intervall = self.gs.screen_refresh_interval_indicator
        else:
            intervall = self.gs.screen_refresh_interval_plotter

        if self._clock.stopwatch_time >= intervall:
            self._clock.reset_stopwatch()
            return True
        return False

    def check_new_samples(self) -> list[int]:
        """returns list of sensors with new samples"""
        rtn = []
        for i, cnt in enumerate(
            map(SensorProcess.get_total_sample_cnt, self.sensor_processes)
        ):
            if self._last_processed_smpl[i] < cnt:
                # new sample
                self._last_processed_smpl[i] = cnt
                rtn.append(i)
        return rtn

    def process_key(self, key):
        if key == misc.constants.K_q or key == misc.constants.K_ESCAPE:
            self.quit_recording = True
        elif key == misc.constants.K_v:
            self.plot_indicator = not self.plot_indicator
            self.background.stimulus().present()
        elif key == misc.constants.K_p:
            # pause
            self.pause_recording = not self.pause_recording
            self.background = self._make_background()
            self.background.stimulus().present()

        elif key == misc.constants.K_b:
            self.background.stimulus("New baseline").present()
            self.recorder.determine_biases()
            sleep(1)
            self.background.stimulus().present()


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

        elif key == misc.constants.K_t:
            tmp = _text2number_array(
                io.TextInput(
                    "Enter thresholds", background_stimulus=logo_text_line("")
                ).get()
            )
            self.background.stimulus().present()
            if tmp is not None:
                self.threshold_list = [Thresholds(tmp)] * self.n_sensors
            else:
                self.threshold_list = []
