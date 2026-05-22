import json
import os
from dataclasses import dataclass, field
from typing import List

import tomlkit
from icecream import ic


@dataclass
class _GUISettings:
    sampling_rate: int = 1000
    level_detection_parameter: str = "Fz"
    window_font: str = "freemono"
    moving_average_size: int = 5
    screen_refresh_interval_indicator: int = 300
    gui_screen_refresh_interval_plotter: int = 50
    data_min_max: list = field(default_factory=lambda: [-5, 30])
    plotter_pixel_min_max: list = field(default_factory=lambda: [-250, 250])
    indicator_pixel_min_max: list = field(default_factory=lambda: [-150, 150])
    plot_axis: bool = False
    plot_data_indicator_for_single_sensor: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)])
    plot_data_plotter_for_single_sensor: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2)])
    plot_data_indicator_for_two_sensors: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
    plot_data_plotter_for_two_sensors: list = field(
        default_factory=lambda: [(0, 2), (1, 2)])

@dataclass
class _RecordingSetting:
    device_name_prefix: str = "Dev"
    device_ids:  List[int] = field(default_factory=lambda: [1])
    ask_filename: bool = False
    remote_control: bool = False
    calibration_folder: str = "calibration"
    calibration_files: List[str] = field(default_factory=lambda: ["FT9334.cal"])
    zip_data: bool = True
    write_Fx: bool = True
    write_Fy: bool = True
    write_Fz: bool = True
    write_Tx: bool = False
    write_Ty: bool = False
    write_Tz: bool = False
    write_trigger1: bool = False
    write_trigger2: bool = False
    lsl_stream: bool = False
    reverse_scaling: dict = field(default_factory=lambda: {"1": ["Fz"], "2": ["Fz"]})
    convert_to_forces: bool = True
    priority: str = "normal"

    def __post_init__(self):
        if isinstance(self.device_ids, int):
            self.device_ids = [self.device_ids]
        if isinstance(self.calibration_files, str):
            self.calibration_files = [self.calibration_files]


class GUISettings(object):

    def __init__(self, filename):
        # defaults
        self.gui = _GUISettings()
        self.gui_section = "GUI"

        self.recording = _RecordingSetting()
        self.recording_section = "Recording"

        self.filename = filename
        if os.path.isfile(self.filename):
            self.load()
        else:
            self.save() # defaults

    def _asdict(self):
        return {self.recording_section: self.recording.__dict__,
             self.gui_section: self.gui.__dict__}

    def set_gui_settings(self, gui_setting_dict):
        self.gui = _GUISettings(**gui_setting_dict)

    def set_recording_setting(self, recording_setting_dict):
        self.recording = _RecordingSetting(**recording_setting_dict)

    def load(self, filename=None):
        if filename is not None:
            self.filename = filename
        with open(self.filename, 'r', encoding='utf-8') as fl:
            d = tomlkit.load(fl)
        self.set_gui_settings(d[self.gui_section])
        self.set_recording_setting(d[self.recording_section])

    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as fl:
            tomlkit.dump(self._asdict(), fl)

    def recording_as_json(self):
        return json.dumps(self.recording.__dict__)

settings = GUISettings(filename="pyForceDAQ.defaults.settings.toml")
