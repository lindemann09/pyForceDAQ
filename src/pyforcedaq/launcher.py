import glob
from os import path
from pathlib import Path
from typing import List

import PySimpleGUI as _sg

from . import __version__, constants
from ._lib.misc import list_settings_files
from ._lib.settings import AppSettings
from ._lib.udp_connection import UDPConnection


def _check_sensor_calibration_settings(
    device_labels: List[str], calibrations_files: List[str], calibration_folder: str
):
    rtn = []
    for x, labels in enumerate(device_labels):
        error = False
        try:
            cal_file = calibrations_files[x]
        except KeyError:
            cal_file = "??"
            error = True

        if not error:
            cal = path.join(calibration_folder, cal_file)
            if not path.isfile(cal):
                cal = "NOT FOUND"
                error = True

        rtn.append([labels, cal_file, error])

    return rtn


def _windows_run(settings: AppSettings):
    rs = settings.recording
    n_sensor = len(rs.device_labels)

    info_settings = []
    lst_settings = list_settings_files()
    info_settings.append(
        [
            _sg.Combo(
                values=lst_settings,
                default_value=settings.filepath.name,
                key="Settings_file",
                size=(34, 1),
                enable_events=True,
                readonly=True,
            )
        ]
    )
    info_settings.append([_sg.Text(f"Number of sensors: {n_sensor}")])
    for labels, cal, error in _check_sensor_calibration_settings(
        rs.device_labels, rs.calibration_files, rs.calibration_folder
    ):
        if error:
            col = "red"
        else:
            col = _sg.DEFAULT_ELEMENT_TEXT_COLOR

        info_settings.append([_sg.Text(f"- {labels}: {cal}", text_color=col)])

    info = [[_sg.Text(f"version: {__version__}")]]
    info.append([_sg.Text(f"IP address: {UDPConnection.MY_IP}")])

    if constants.DAQ_TYPE == constants.MOCK_SENSOR:
        info.append([_sg.Text("!!!  USING MOCK SENSORS  !!!", text_color="red")])

    layout = [
        [
            _sg.Button(
                "Start Recording",
                size=(32, 4),
                button_color=("black", "lightgreen"),
                key="Start",
            )
        ],
        [_sg.Frame("Info", size=(280, 150), layout=info)],
        [_sg.Frame("Settings", size=(280, 140), expand_y=True, layout=info_settings)],
    ]
    layout.append(
        [
            _sg.Frame(
                "Data Output",
                size=(280, 80),
                layout=[
                    [
                        _sg.Text("Filename:", size=(8, 1)),
                        _sg.Input(default_text="", size=(24, 1), key="datafilename"),
                    ],
                    [
                        _sg.Checkbox("Save Data", rs.save_data, key="save_data"),
                        _sg.Checkbox("LSL stream", rs.lsl_stream, key="lsl"),
                    ],
                ],
            )
        ]
    )

    layout.append(
        [
            _sg.Button("Save settings", size=(12, 2), key="Save"),
            _sg.Cancel(size=(12, 2)),
        ]
    )

    window = _sg.Window("ForceGUI".format(), layout)
    event, values = window.read()

    settings.recording.lsl_stream = values["lsl"]
    settings.recording.save_data = values["save_data"]
    if len(values["datafilename"]) > 3:
        settings.output_filename = values["datafilename"]
        settings.recording.save_data = True

    window.close()
    return event, values, settings


def load_settings_file(settings_file: str | Path) -> AppSettings:
    settings = AppSettings(filename=settings_file)

    rs = settings.recording
    settings_error = False
    n_sensor = len(rs.device_labels)
    if n_sensor != len(rs.calibration_files):
        _sg.PopupError("Number of devices and calibration files are not equal.")
        settings_error = True

    if not path.isdir(rs.calibration_folder):
        _sg.PopupError(f"Can't find calibration folder: {rs.calibration_folder}")
        settings_error = True
    if settings_error:
        exit()
    return settings


def run_launcher():
    _sg.theme("DarkBlue14")  # please make your windows colorful

    toml_files = glob.glob("*.toml")
    if len(toml_files) == 0:
        settings_file = constants.DEFAULT_SETTINGS_FILE
    else:
        settings_file = toml_files[0]
    settings = load_settings_file(settings_file)

    while True:
        event, values, settings = _windows_run(settings)

        if event == "Save":
            settings.save()
        elif event == "Settings_file":
            settings = load_settings_file(values["Settings_file"])
        else:
            break

    if event == "Start":
        if not (settings.recording.save_data or settings.recording.lsl_stream):
            ch = _sg.popup_yes_no(
                "You have not selected any data output. "
                + "Are you sure you want to continue?",
                title="No data output selected!",
            )
            if ch == "No":
                return  # quit
        from . import gui

        gui.run(settings)
    else:
        pass
