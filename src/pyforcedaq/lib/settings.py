import json
from abc import ABC
from dataclasses import dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import tomlkit
from icecream import ic
from tomlkit.exceptions import NonExistentKey

from ..constants import SETTINGS_FILE_EXTENSION


class NIDAQConfiguration(object):
    """Settings required for NI-DAQ"""

    def __init__(
        self,
        device_name: str,
        channels: str ,
        rate: int,
        minVal: float,
        maxVal: float,
    ):
        self.device_name = device_name
        self.channels = channels
        self.rate = rate
        self.minVal = minVal
        self.maxVal = maxVal

    @property
    def physicalChannel(self):
        return "{0}/{1}".format(self.device_name, self.channels)


@dataclass
class SensorSettings(NIDAQConfiguration):
    """
    :parameter:
        reverse_parameter_names: string or list of strings
            list of parameter names for which the scaling needs to be reversed (e.g. to fix problems with calibration),
            Sensors take this into account and correct data online
    """

    sensor_id: int
    device_label: str
    calibration_file: Path
    # DAQ settings
    channels: str
    rate: int = 1000
    convert_to_FT: bool = True
    minVal: float = -10
    maxVal: float = 10
    reverse_parameter_names: str | Tuple[str] | List[str] | None = None

    def __post_init__(self):

        super().__init__(
            device_name=f"{self.device_label}",
            channels=self.channels,
            rate=self.rate,
            minVal=self.minVal,
            maxVal=self.maxVal,
        )



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
    device_labels: List[str] = field(default_factory=lambda: ["Dev1"])
    device_channels: List[str] = field(default_factory=lambda: ["ai0:7"])
    calibration_files: List[str] = field(default_factory=lambda: ["FT9334.cal"])
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

    reverse_scaling: dict | None = field(
        default_factory=lambda: {"Dev1": [], "Dev2": ["Fz"]}
    )
    convert_to_forces: bool = True
    zip_data: bool = False

    priority: str | None = "normal"

    def __post_init__(self):

        if isinstance(self.device_labels, str):
            self.device_labels = [self.device_labels]
        if isinstance(self.calibration_files, str):
            self.calibration_files = [self.calibration_files]
        if isinstance(self.device_channels, str):
            self.device_channels = [self.device_channels]

    def set_properties(self, property_dict: Dict[str, Any]) -> bool:
        """return true if a properties of the data class is
        missing or changed in the dict"""

        rtn = super().set_properties(property_dict)
        assert is_dataclass(self)

        n = len(self.device_labels)
        if len(self.calibration_files) == 1 and n>1:
            self.calibration_files = self.calibration_files * n
            rtn = True
        if len(self.device_channels) == 1 and n>1:
            self.device_channels = self.device_channels * n
            rtn = True
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

    def reverse_parameters_for_device(self, label: str):
        if self.reverse_scaling is None:
            return []
        else:
            try:
                return self.reverse_scaling[label]
            except KeyError:
                return []

    def sensor_settings_list(self, working_dir: str | Path) -> List[SensorSettings]:
        rtn: List[SensorSettings] = []
        for label, cal_file, channels in zip(self.device_labels, self.calibration_files, self.device_channels):
            cal_file_path = self.absolute_path_calibration(working_dir) / cal_file
            ss = SensorSettings(
                sensor_id=self.device_labels.index(label) + 1,
                device_label=label,
                channels=channels,
                calibration_file=cal_file_path,
                reverse_parameter_names=self.reverse_parameters_for_device(label),
                rate=self.sampling_rate,
                convert_to_FT=self.convert_to_forces,
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

        a = self.gui.set_properties(d[self.gui_section])
        b = self.recording.set_properties(d[self.recording_section])
        if a or b:
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