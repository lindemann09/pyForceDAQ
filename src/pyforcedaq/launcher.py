from os import path
from pathlib import Path

import PySimpleGUI as _sg

from . import __version__, constants
from .lib.lan_tools import get_lan_ip
from .lib.settings import AppSettings, SensorSettings, list_settings_files

#icon converted with psgresizer
APP_ICON = b'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87LLLl1w1113UdWUY5AC0AELFy48OmLEiEdUNT5FJpIzs63OjYeX1OOJjxh2GfkIal6xU1GI6dA1E1yj3YOpByB1Qg7CYLQq0loW3B1Gjx798v33P2D7qH9rZAzgLPzTP9327s6du2b3zschaZdwAKW5KkZkceT6VLhcbqhULh1pPkLbllF5dVB1440vqxGiluddYNiwkoNXXDFjwv33P+i44K8sBDoLM2fOvL+q6tT7J06cGNk7H4mkDS4vdtdD3CysSsq2UNC2a8afmZlZd9FFF97jROMn5BTgLHz96/fuLywsnJuTk9PzLW0kSYWmaZh11azfPProY/FfB5KkyClAJ7n77rvv2LRp01/j+3FIejPjMHLkyOdfeeWVbzj5qksPoJPMnz//lQsvuOAfidhUVBJ7zjnnnO0PPfTQj5x+baUAdJIrr7zSyM/v+8+jRo2yXW94p1FcXHz43HPPnXXxxRcfhcORw1kX+fOf/zzonXfeWbtr166i+HwkkngyePDg0Ny5c+++8847X5FXWnoAXebuu+8+ePWsq2YNGjSoQn6BUov8/HzzlltumS+Nvwk5BegG9yz42pfz5s2bVlxcLEUgRcjPzw9cddVV8+6+++5XE30uyYQUgG5y++2377z22muvLCkpORLbj0QSawr6FQRmzZp1z3e/+92/y6vbEhkD6CHPPffshPfee++9/fvLC3t6LEnsKSws1G+88cb59913n21be/cEKQAx4PXXXxvzpz/9+Y8HDx6cHIvjSWJDRkbGrq9+9Z67Fiy451N5TdtHCkCMuO666zS32/1qeXn5HKPZBqCSxFBSUrKtuLh41q9+9ate2/QlFZECEENeeOE53+bNX/7xk08+maPruieWx5Z0vrz3kksuWTdp0qS5d9555wF53c6MFIA48Pjjj9+5du3aP5w6dapX9huUWHi9XmPq1Kkv9OvX74HHHntMNnXsBFIA4sTcubcMDIX0leXl5SXxeg1JE0VFA+oGDx5007PPPvuhvC6dRwpAHFm2bNmQRYsWLdy6desdfr+jGs30GtSwpbS09JO5c2979JZbbl6T6PNJNaQAxJn169e7X3755eu3bt36/PHjx/ucdSdcSafp06dP/fjx439x8803/+dll11WLS9d15EC0Es8+eSTefv27Xt+27Ztc4LBoLzuPYBWZI4ZM2b9pZde+sA3vvGN9bH7lJyH/CL2Mo8//viU7du3/2H//v1je/u17UBBQcHha6655tmrr7766ZEjRwYTfT6pjhSABPDXv/4lbf/+8v9YtWrV/BMnTubJacHZycvLaxw/fvxLbrf70Z/+9Kcdb0Ao6RJSABLI737326KNGzfdv3fv3ocqqyozrY0BJc1JT08PjBs37p3x48f/8P77798qr05skQKQBLz4338oevMfb36zrrb2kerq6rREn08y4PV6yd1fdN555z31ox/9SBp+nJACkEQ888wzfb/44ovvHT169J6qqqq+cCA5OTn68OHDV8+ePfs/Dxw48Na3v/1t6RfFESkAScjChQvz/H7/41u2bJlz4sSJErvXECiKgv79+zeOGjXqraFDh/7kwQcf3Jzoc3IKUgCSmOXLP/Rs27Zj7sqVK289duzY7Lq6OrddAoaUyvN4PMaoUaNP5uX1/fn06dPfveaaa3Yk+rychhSAFGHx4sXjli9ffsOGDRsmhsPhm0+dSs19LDweD3XnKS8qKnrr8ukz3rh93j+vSPQ5ORkpACnIvffem5aTk3PfyZMnbzly5MjoysrKnHA4jGQd6fPz85GVlbVz4MCB71100UWvNTQ0rL/nnnvkRitJgBSAFOftt98q/HjNJyUVxyquDIfD1+7du7ePpqlD6+sbmNnNnXJ7OsK7XK7afv0KTubn5306fvz4DYZh/O/s2bMrSktLT2/uJUkOpADYkOeff/biZcuWZffr13/OoUOHBqWlpV1+4MABNDY2ejjnCglDd2MJNKJT0I5utG93UVERrcHfHgwGP5s4cWLFiRMnPpgzZ86RWbNmlcX6fUlijxQAB/HZZ59dvmLFivzVq1ejpqbGN23atFuPHz9OP5M4IBgMQtd1IQ6RIB18Ph9toEkLb+i+Q1988cXySy65BBdccAGfPXv2a4l+TxKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRIKe8P8BdZ4rUS6POmsAAAAASUVORK5CYII='


def _check_sensor_calibration_settings(sensors:list[SensorSettings]):
    rtn = []
    for sensor in sensors:
        error = False
        cal_file = sensor.calibration_file_name

        if not error:
            cal = sensor.calibration_folder / sensor.calibration_file_name
            if not path.isfile(cal):
                cal = "NOT FOUND"
                error = True

        rtn.append([sensor.device_label, cal_file, error])

    return rtn

def _windows_run(settings: AppSettings, lst_settings: list[str]):
    rs = settings.recording
    working_dir = settings.file.parent
    n_sensor = len(rs.sensors)

    info_settings = []
    info_settings.append(
        [
            _sg.Combo(
                values=lst_settings,
                default_value=settings.file.name,
                key="Settings_file",
                size=(34, 1),
                enable_events=True,
                readonly=True,
            )
        ]
    )
    info_settings.append([_sg.Text(f"Number of sensors: {n_sensor}")])
    for labels, cal, error in _check_sensor_calibration_settings(rs.get_sensor_settings(working_dir)):
        if error:
            col = "red"
        else:
            col = _sg.DEFAULT_ELEMENT_TEXT_COLOR

        info_settings.append([_sg.Text(f"- {labels}: {cal}", text_color=col)])

    info = [[_sg.Text(f"version: {__version__}")]]
    info.append([_sg.Text(f"IP address: {get_lan_ip()}")])

    if constants.DAQ_TYPE == constants.DaqType.MOCK_SENSOR:
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

    _sg.set_global_icon(APP_ICON)
    window = _sg.Window("ForceGUI".format(), layout)
    event, values = window.read()

    settings.recording.lsl_stream = values["lsl"]
    settings.recording.save_data = values["save_data"]
    if len(values["datafilename"]) > 3:
        settings.output_filename = values["datafilename"]
        settings.recording.save_data = True

    window.close()
    return event, values, settings


def _load_settings_file(settings_file: str | Path) -> AppSettings:
    settings = AppSettings(filename=settings_file)

    rs = settings.recording
    settings_error = False
    if not path.isdir(rs.calibration_folder):
        _sg.PopupError(f"Can't find calibration folder: {rs.calibration_folder}")
        settings_error = True
    if settings_error:
        exit()
    return settings


def run_launcher():
    _sg.theme("DarkBlue14")  # please make your windows colorful

    app_setting_files = list_settings_files()
    if len(app_setting_files) == 0:
        raise FileNotFoundError("No settings files found. Please create a settings file first.")
    else:
        settings_file = app_setting_files[0]
    settings = _load_settings_file(settings_file)
    while True:
        event, values, settings = _windows_run(settings, app_setting_files)

        if event == "Save":
            settings.save()
        elif event == "Settings_file":
            settings = _load_settings_file(values["Settings_file"])
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
