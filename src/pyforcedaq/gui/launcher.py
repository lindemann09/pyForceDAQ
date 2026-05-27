from os import path
from typing import List

import PySimpleGUI as _sg

from .. import USE_MOCK_SENSOR, __version__
from .._lib.settings import DEFAULT_SETTINGS_FILE, AppSettings, RecordingSettings
from .._lib.udp_connection import UDPConnection
from . import _run


def _check_sensor_calibration_settings(device_ids: List[int],
                                       calibrations_files : List[str],
                                       calibration_folder :str):
    rtn = []
    for x, d_id in enumerate(device_ids):
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

        rtn.append([d_id, cal_file, error])

    return rtn


def _windows_run(rs: RecordingSettings):
    n_sensor = len(rs.device_ids)

    info_settings = []
    info_settings.append([_sg.Text(f"Number of sensors: {n_sensor}")])

    for d_id, cal, error in _check_sensor_calibration_settings(
                                                rs.device_ids,
                                                rs.calibration_files,
                                                rs.calibration_folder):
        if error:
            col = "red"
        else:
            col = _sg.DEFAULT_ELEMENT_TEXT_COLOR

        info_settings.append([_sg.Text(f"- {rs.device_name_prefix}{d_id}: {cal}",
                              text_color=col)])

    info = [[_sg.Text(f"forceDAQ version: {__version__}")]]
    info.append([_sg.Text(f"IP address: {UDPConnection.MY_IP}")])
    if USE_MOCK_SENSOR:
        info.append([_sg.Text("!!!  USING MOCK SENSORS  !!!",
                              text_color="red")])

    layout = [[_sg.Button("Start Recording", size=(29, 4),
                          button_color=('black', 'lightgreen'),
                          key="Start")],
              [_sg.Frame('Settings', info_settings)],
              [_sg.Frame('Info', info)],
              [_sg.Button("Edit Settings", key="Settings", size=(12, 2)),
               _sg.Cancel(size=(12, 2))]]

    window = _sg.Window('ForceGUI'.format(), layout)
    event, values = window.read()
    window.close()
    return event, values


def run_launcher():
    _sg.theme('DarkBlue14')  # please make your windows colorful
    settings = AppSettings(filename=DEFAULT_SETTINGS_FILE)

    rs = settings.recording
    settings_error = False
    n_sensor = len(rs.device_ids)
    if n_sensor != len(rs.calibration_files):
        _sg.PopupError("Number of devices IDs and calibration files are not equal.")
        settings_error = True

    if not path.isdir(rs.calibration_folder):
        _sg.PopupError("Can't find calibration folder: {}".format(
            rs.calibration_folder))
        settings_error = True
    if settings_error:
        return

    while True:
        event, _ = _windows_run(rs)
        if event == "Converter":
            pass
        else:
            break

    if event == "Start":
        _run.run(settings)
    else:
        pass
