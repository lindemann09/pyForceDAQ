import sys
from os import path

import PySimpleGUI as _sg
from .. import __version__, USE_DUMMY_SENSOR
from .._lib.misc import find_calibration_file
from ._settings import settings
from ._run import run as _gui_run
from .._lib.udp_connection import UDPConnection
from .._lib.types import PollingPriority



def _group(title, objects):
    return [_sg.Frame(title, [objects])]


def _input_text_list(lable, list, key, x_sizes=(19, 20)):
    return [_sg.Text(lable, size=(x_sizes[0], 1)),
            _sg.Input(default_text=_l2s(list), size=(x_sizes[1], 1), key=key)]

def _l2s(the_list): #convert list to str
    text_list = "{}".format(the_list)
    return text_list.replace("[","").replace("]","").replace("'", "")

def _s2l(csv_string, is_integer=False, is_float=False): # convert csv string to list
    rtn = []
    for x in csv_string.split(","):
        x = x.strip()
        if is_float:
            x = float(x)
        elif is_integer:
            x = int(x)
        rtn.append(x)
    return rtn

def _check_sensor_calibration_settings(device_ids, sensor_names,
                                       calibration_folder):
    rtn = []
    for x, d_id in enumerate(device_ids):
        error = False
        try:
            sensor_name = sensor_names[x]
        except:
            sensor_name = "??"
            error = True
        try:
            cal = find_calibration_file(calibration_folder=calibration_folder,
                                    sensor_name=sensor_name)
        except:
            cal = "NO CALIBRATION"
            error = True
        rtn.append([d_id, sensor_name, cal, error])

    return rtn

def _windows_run():
    s = settings.recording
    n_sensor = len(s.device_ids)

    info_settings = []
    info_settings.append([_sg.Text("Remote Control: {}".format(s.remote_control))])
    info_settings.append([_sg.Text("Number of sensors: {}".format(n_sensor))])

    for d_id, name, cal, error in _check_sensor_calibration_settings(
                                                s.device_ids,
                                                s.sensor_names,
                                                s.calibration_folder):
        if error:
            col = "red"
        else:
            col = _sg.DEFAULT_ELEMENT_TEXT_COLOR

        info_settings.append([_sg.Text("- {}{}: {}, {}".format(s.device_name_prefix,
                                                      d_id, name, cal),
                              text_color=col)])

    info = [[_sg.Text("forceDAQ version: {}".format(__version__))]]
    info.append([_sg.Text("IP address: {}".format(UDPConnection.MY_IP))])
    if USE_DUMMY_SENSOR:
        info.append([_sg.Text("!!!  USING DUMMY SENSORS  !!!",
                              text_color="red")])

    layout = [
              [_sg.Button("Start Recording", size=(29, 4),
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

def _window_settings():
    s = settings.recording
    layout = []

    #layout.append([sg.Text('Recording Settings')])
    layout.append([_sg.Frame('General',
                         [[_sg.Checkbox("Remote Control", s.remote_control,
                                       key="remote_control"),
                           _sg.Checkbox("Enter Filename Manually",
                                        s.ask_filename, key="ask_filename")],
                          [_sg.Checkbox("Zip Data", s.zip_data,
                                       key="zip_data")],
                          [_sg.Text('Process Priority'),
                            _sg.Combo((PollingPriority.NORMAL,
                                       PollingPriority.HIGH,
                                       PollingPriority.REALTIME),
                                      size=(10, 10),
                                      default_value=s.priority,
                                      key='priority')]
                          ])])


    layout.append([_sg.Frame('Sensor',
                             [_input_text_list("Device Name Prefix:",
                                               s.device_name_prefix,
                                      key="device_name_prefix"),
                              _input_text_list("Device IDs:",
                                               s.device_ids,
                                      key="device_ids")]
                             )])

    layout.append([_sg.Frame('Calibration',
                 [[_sg.Text("Folder:", size=(5, 1)), _sg.InputText(
                     s.calibration_folder, size=(23, 1), key="cal_dir"),
                  _sg.FolderBrowse(size=(6, 1))],
                 _input_text_list("Sensor Names:", s.sensor_names,
                          key="sensor_names")
                 ])])

    layout.append([_sg.Frame('Record Forces & Torques',
                         [[_sg.Checkbox("Fx", s.write_Fx, key="write_Fx"),
                          _sg.Checkbox("Fy", s.write_Fy, key="write_Fy"),
                          _sg.Checkbox("Fz", s.write_Fz, key="write_Fz"),
                          _sg.Checkbox("Tx", s.write_Tx, key="write_Tx"),
                          _sg.Checkbox("Ty", s.write_Ty, key="write_Ty"),
                          _sg.Checkbox("Tz", s.write_Tz, key="write_Tz")],
                         [_sg.Checkbox("Convert Voltage to Force Online",
                                       s.convert_to_forces,
                                      key="convert_to_forces")]
                          ])])

    # reverse scaling FIXME DOES NOT WORK
    tmp = []
    for x in s.device_ids:
        try:
            l = s.reverse_scaling[str(x)]
        except:
            l = []
        tmp.extend(_input_text_list("{}:".format(x), l, x_sizes=(1, 10),
                                    key="revscal{}".format(x)))
    layout.append(_group('Reverse scaling', tmp))


    layout.append([_sg.Frame('',
                   [[_sg.Checkbox("Trigger1", s.write_trigger1,
                                 key="write_trigger1"),
                    _sg.Checkbox("Trigger2", s.write_trigger2,
                                 key="write_trigger2")]
                   ])])

    layout.append([_sg.Save(), _sg.Cancel()])

    window =  _sg.Window('ForceGUI {}: Settings'.format(__version__), layout)
    event, values = window.read()

    d = s._asdict()
    if event=="Save":
        ## todo write settings
        for key in ("device_name_prefix", "remote_control", "ask_filename",
                    "write_Fx", "write_Fy", "write_Fz",
                    "write_Tx", "write_Ty", "write_Tz",
                    "write_trigger1", "write_trigger2", "convert_to_forces",
                    "zip_data", "priority"):
            d[key] = values[key]

        key = "device_ids"
        try:
            d[key] = _s2l(values[key], is_integer=True)
        except:
            event = "Error"

        key = "sensor_names"
        try:
            d[key] = _s2l(values[key])
        except:
            event = "Error"

        # reverse scaling dicts
        for x in s.device_ids:
            try:
                d["reverse_scaling"][str(x)] = _s2l(values["revscal{}".format(x)])
            except:
                event = "Error"

        # calibration file
        main_path = path.split(sys.modules['__main__'].__file__)[0] + path.sep
        d["calibration_folder"] = values["cal_dir"].replace(main_path, "")

        settings.set_recoding_setting(d)
        settings.save()

    window.close()
    return event

def run():
    _sg.theme('DarkBlue14')  # please make your windows colorful
    s = settings.recording
    settings_error = False
    n_sensor = len(s.device_ids)
    if n_sensor != len(s.sensor_names):
        _sg.PopupError("Number of devices IDs and sensor names are "
                       "not equal.")
        settings_error = True

    if not path.isdir(s.calibration_folder):
        _sg.PopupError("Can't find calibration folder: {}".format(
            s.calibration_folder))
        settings_error = True

    if settings_error:
        _window_settings()

    while True:
        event, _ = _windows_run()
        if event == "Settings":
            if _window_settings() == "Error":
                _sg.PopupError("Something is wrong with the settings.")
        else:
            break

    if event == "Start":
        _gui_run()
    else:
        pass
