import json
from abc import ABC
from dataclasses import dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

import tomlkit
from tomlkit.exceptions import NonExistentKey

from ..constants import SETTINGS_FILE_EXTENSION


@dataclass(frozen=True)
class SensorSettings:
    """basic settings for a sensor that are in the toml settings file
    :parameter:
        reverse_scaling: ist of strings
            list of parameter names for which the scaling needs to be reversed (e.g. to fix problems with calibration),
            Sensors take this into account and correct data online
    """

    device_label: str
    channels: str
    calibration_file_name: str
    calibration_folder: Path
    sensor_id: int
    reverse_scaling: List[str]
    rate: int
    convert_to_FT: bool
    minVal: float
    maxVal: float

    @property
    def physicalChannel(self):
        return "{0}/{1}".format(self.device_label, self.channels)


class ABCSettings(ABC):  # must be a dataclass

    def set_properties(self, property_dict: Dict[str, Any]) -> bool:
        """return true is a properties of the data class is
        missing in the dict"""
        assert is_dataclass(self)

        for key, values in property_dict.items():
            if hasattr(self, key):
                setattr(self, key, values)
        # check all properties in dataclass have been set
        for class_property in self.__dataclass_fields__.keys():  # type: ignore
            if class_property not in property_dict:
                return True
        return False


@dataclass
class RecordingSettings(ABCSettings):

    sensors: List[dict] = field(default_factory=lambda: [
        {"device_label": "Dev1",
         "channels": "ai0:7",
         "calibration_file_name": "FT9334.cal",
         "reverse_scaling": ["Fz"]}])

    calibration_folder: str = "./calibration"
    data_folder: str = "./data"

    lsl_stream: bool = True
    save_data: bool = False
    sampling_rate: int = 1000

    write_Fx: bool = True
    write_Fy: bool = True
    write_Fz: bool = True
    write_Tx: bool = False
    write_Ty: bool = False
    write_Tz: bool = False
    write_trigger1: bool = False
    write_trigger2: bool = False

    convert_to_forces: bool = True
    zip_data: bool = False

    priority: str | None = "normal"

    def __post_init__(self):
        self._check_sensor_settings()

    def _check_sensor_settings(self):
        if not isinstance(self.sensors, list):
            raise ValueError("Sensors must be a list of dictionaries with the four sensor properties: "
                             "     device_label, channels, calibration_file_name, reverse_scaling")
        for s in self.sensors:
            if not("device_label" in s and "channels" in s and "calibration_file_name" in s):
                raise ValueError("Each sensor dictionary must have a device_label, channels, and calibration_file_name")
            if "reverse_scaling" not in s:
                s["reverse_scaling"] = []

    def set_properties(self, property_dict: Dict[str, Any]) -> bool:
        """return true if a properties of the data class is
        missing or changed in the dict"""

        assert is_dataclass(self)
        rtn = super().set_properties(property_dict)
        self._check_sensor_settings()
        return rtn

    def absolute_path_calibration(self, working_dir: str | Path) -> Path:
        fld = Path(self.calibration_folder)
        if fld.is_absolute():
            return fld
        else:
            return Path(working_dir).absolute() / fld

    def absolute_path_data(self, working_dir: str | Path) -> Path:
        fld = Path(self.data_folder)
        if fld.is_absolute():
            return fld
        else:
            return Path(working_dir).absolute() / fld


    def array_write_forces(self):
        return [
            self.write_Fx,
            self.write_Fy,
            self.write_Fz,
            self.write_Tx,
            self.write_Ty,
            self.write_Tz,
        ]

    def array_write_trigger(self):
        return [self.write_trigger1, self.write_trigger2]

    def get_sensor_settings(self, working_dir: str | Path) -> List[SensorSettings]:

        rtn: List[SensorSettings] = []
        for cnt,sensor in enumerate(self.sensors):
            ss = SensorSettings(
                device_label=sensor["device_label"],
                calibration_file_name=sensor["calibration_file_name"],
                channels=sensor["channels"],
                reverse_scaling=sensor["reverse_scaling"],
                sensor_id=cnt + 1,
                calibration_folder=self.absolute_path_calibration(working_dir),
                rate=self.sampling_rate,
                convert_to_FT=self.convert_to_forces,
                minVal=-10,
                maxVal=10
            )
            rtn.append(ss)
        return rtn


@dataclass
class GUISettings(ABCSettings):

    level_detection_parameter: str = "Fz"
    window_font: str = "freemono"
    moving_average_size: int = 5
    screen_refresh_interval_indicator: int = 300
    screen_refresh_interval_plotter: int = 50
    data_min_max: list = field(default_factory=lambda: [-5, 30])
    plotter_pixel_min_max: list = field(default_factory=lambda: [-250, 250])
    indicator_pixel_min_max: list = field(default_factory=lambda: [-150, 150])
    plot_axis: bool = False
    plot_data_indicator_for_single_sensor: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]
    )
    plot_data_plotter_for_single_sensor: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2)]
    )
    plot_data_indicator_for_two_sensors: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
    )
    plot_data_plotter_for_two_sensors: list = field(
        default_factory=lambda: [(0, 2), (1, 2)]
    )


class AppSettings(object):

    def __init__(self, filename: str | Path, create_if_not_exists: bool = False):
        # defaults
        self.gui = GUISettings()
        self.gui_section = "GUI"

        self.recording = RecordingSettings()
        self.recording_section = "Recording"

        self.file = Path(filename)
        self.file = self.file.with_suffix(SETTINGS_FILE_EXTENSION)
        if self.file.exists():
            self.load()
        else:
            if create_if_not_exists:
                self.save()  # defaults
                print(f"Creating new settings file with defaults: {self.file}")
            else:
                raise FileNotFoundError(f"Settings file {self.file} not found")

        self.output_filename:str = ""

    def _asdict(self):
        return {
            self.recording_section: self.recording.__dict__,
            self.gui_section: self.gui.__dict__
        }

    def load(self, filename: str | Path | None = None):
        if filename is not None:
            self.file = Path(filename)
        with open(self.file, "r", encoding="utf-8") as fl:
            d = tomlkit.load(fl)

        do_save= False
        rec_section = d[self.recording_section]
        if "device_labels" in rec_section:
            # old settings convert to new format
            rec_section = old_recording_settings_to_new(rec_section)
            do_save =True

        a = self.gui.set_properties(d[self.gui_section])
        b = self.recording.set_properties(rec_section)
        if a or b or do_save:
            # missing property in settings file
            self.save()

    def save(self):

        txt = tomlkit.dumps(self._asdict())
        with open(self.file, "w", encoding="utf-8") as fl:
            fl.write(txt)

    @property
    def recording_as_json(self):
        return json.dumps(self.recording.__dict__)


def list_settings_files():
    """Returns a list of all settings files in the current directory."""
    rtn = []
    for f in Path(".").glob(f"*{SETTINGS_FILE_EXTENSION}"):
        try:
            AppSettings(f)  # try to load settings file to check if it's valid
            rtn.append(f.name)
        except NonExistentKey:
            pass

    return rtn


def old_recording_settings_to_new(d: dict):
    """ensures backward compatibility with old settings files
    that used device_labels, device_channels, calibration_files

    DEPRECATED
    """

    s = []
    for dev, channels, cal_file in zip(d["device_labels"], d["device_channels"], d["calibration_files"]):
        rev_scaled = d["reverse_scaling"].get(dev, [])
        s.append({
            "device_label": dev,
            "channels": channels,
            "calibration_file_name": cal_file,
            "reverse_scaling": rev_scaled
        })
    d["sensors"] = s
    del d["device_labels"]
    del d["device_channels"]
    del d["calibration_files"]
    del d["reverse_scaling"]
    return d
