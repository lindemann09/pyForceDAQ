import json
import os
from abc import ABC
from dataclasses import dataclass, field, is_dataclass
from os import path
from pathlib import Path
from typing import Any, Dict, List, Tuple

import tomlkit

from .types import ForceSensorData

DEFAULT_SETTINGS_FILE = "pyForceDAQ.defaults.settings.toml"
DATA_FOLDER = "data"

class DAQConfiguration(object):
    """Settings required for NI-DAQ"""
    def __init__(self,
                 device_name: str,
                 channels: str = "ai0:7",
                 rate: int = 1000,
                 minVal: float = -10,
                 maxVal: float = 10):
        self.device_name = device_name
        self.channels = channels
        self.rate = rate
        self.minVal = minVal
        self.maxVal = maxVal

    @property
    def physicalChannel(self):
        return "{0}/{1}".format(self.device_name, self.channels)



@dataclass
class SensorSettings(DAQConfiguration):
    """
    :parameter:
        reverse_parameter_names: string or list of strings
            list of parameter names for which the scaling needs to be reversed (e.g. to fix problems with calibration),
            Sensors take this into account and correct data online
    """
    device_id: int
    sensor_name: str # FIXME maybe not needed, can be derived from calibration file name
    calibration_file: str
    device_name_prefix: str
    # DAQ settings
    channels: str = "ai0:7"
    rate: int = 1000
    minVal: float = -10
    maxVal: float = 10
    convert_to_FT: bool = True
    reverse_parameter_names: str | Tuple[str] | List[str] | None = None

    def __post_init__(self):
        super().__init__(device_name=f"{self.device_name_prefix}{self.device_id}",
                         channels=self.channels,
                         rate=self.rate, minVal=self.minVal, maxVal=self.maxVal)
        self.reverse_parameters: List[int] = []
        if self.reverse_parameter_names is not None:
            names = [self.reverse_parameter_names] if isinstance(self.reverse_parameter_names, str) else self.reverse_parameter_names
            for para in names:
                try:
                    self.reverse_parameters.append(ForceSensorData.forces_names.index(para))
                except Exception:
                    pass



class ABCSettings(ABC): # must be a dataclass

    def set_properties(self, property_dict: Dict[str, Any]) -> bool:
        """return true is a properties of the data class is
        missing in the dict"""
        assert(is_dataclass(self))

        for key, values in property_dict.items():
            if hasattr(self, key):
                setattr(self, key, values)
        # check all properties in dataclass have been set
        for class_property in self.__dataclass_fields__.keys(): # type: ignore
            if class_property not in property_dict:
                return True
        return False

@dataclass
class RecordingSettings(ABCSettings):
    device_name_prefix: str = "Dev"
    device_ids:  List[int] = field(default_factory=lambda: [1])
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
    save_data: bool = True
    reverse_scaling: dict | None = field(default_factory=lambda: {"1": ["Fz"], "2": ["Fz"]})
    convert_to_forces: bool = True
    sampling_rate: int = 1000
    priority: str | None = "normal"

    def __post_init__(self):
        if isinstance(self.device_ids, int):
            self.device_ids = [self.device_ids]
        if isinstance(self.calibration_files, str):
            self.calibration_files = [self.calibration_files]

    def array_write_forces(self):
        return [self.write_Fx, self.write_Fy, self.write_Fz, self.write_Tx, self.write_Ty, self.write_Tz]

    def array_write_trigger(self):
        return [self.write_trigger1, self.write_trigger2]

    def reverse_parameters_for_device(self, device_id: int):
        if self.reverse_scaling is None:
            return []
        else:
            try:
                return self.reverse_scaling[str(device_id)]
            except KeyError:
                return []

    def sensor_settings_list(self)->List[SensorSettings]:
        rtn: List[SensorSettings] = []
        for d_id, cal_file in zip(self.device_ids, self.calibration_files):
            ss = SensorSettings(device_id = d_id,
                        device_name_prefix=self.device_name_prefix,
                        sensor_name = cal_file.split(".")[0],
                        calibration_file=str(Path(self.calibration_folder) / cal_file),
                        reverse_parameter_names=self.reverse_parameters_for_device(d_id),
                        rate = self.sampling_rate,
                        convert_to_FT=self.convert_to_forces
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
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)])
    plot_data_plotter_for_single_sensor: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2)])
    plot_data_indicator_for_two_sensors: list = field(
        default_factory=lambda: [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
    plot_data_plotter_for_two_sensors: list = field(
        default_factory=lambda: [(0, 2), (1, 2)])



class AppSettings(object):

    def __init__(self, filename: str | Path):
        # defaults
        self.gui = GUISettings()
        self.gui_section = "GUI"

        self.recording = RecordingSettings()
        self.recording_section = "Recording"

        self.filepath = Path(filename)
        if os.path.isfile(self.filepath):
            self.load()
        else:
            self.save() # defaults

    def _asdict(self):
        return {self.recording_section: self.recording.__dict__,
             self.gui_section: self.gui.__dict__}

    def load(self, filename=None):
        if filename is not None:
            self.filepath = Path(filename)
        with open(self.filepath, 'r', encoding='utf-8') as fl:
            d = tomlkit.load(fl)

        a = self.gui.set_properties(d[self.gui_section])
        b = self.recording.set_properties(d[self.recording_section])
        if a or b:
            # missing property in settings file ->
            self.save()

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as fl:
            tomlkit.dump(self._asdict(), fl)

    @property
    def recording_as_json(self):
        return json.dumps(self.recording.__dict__)

    @property
    def data_folder(self) -> Path:
        return self.filepath.parent / DATA_FOLDER
