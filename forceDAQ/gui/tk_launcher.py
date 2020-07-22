import PySimpleGUI as _sg
from .. import __version__
from ._settings import settings
from ._run import run as _gui_run

def _group(title, objects):
    return [_sg.Frame(title, [objects])]


def _input_text_list(lable, list, key):
    return [_sg.Text(lable, size=(15, 1)), _sg.Input(default_text=_l2s(list), key=key)]


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


def _run_window():
    s = settings.recording

    n_sensor = len(s.device_ids)
    if n_sensor != len(s.sensor_names):
        _sg.PopupError("Number of devices IDs and sensor names are "
                       "not equal.")

    info = []
    info.append([_sg.Text("Remote Control: {}".format(s.remote_control))])
    info.append([_sg.Text("Number of sensors: {}".format(n_sensor))])
    for x in range(n_sensor):
        try:
            name = s.sensor_names[x]
        except:
            name = "??"
        info.append([_sg.Text("- {}{}: {}".format(s.device_name_prefix,
                                                 s.device_ids[x], name))])


    layout = [
              [_sg.Button("Start Recording", size=(29, 4),
                          button_color=('black', 'green'),
                          key="Start")],
              [_sg.Frame('Settings', info)],
              [_sg.Button("Edit Settings", key="Settings", size=(12, 2)),
               _sg.Cancel(size=(12, 2))]]

    window = _sg.Window('ForceGUI {}'.format(__version__), layout)
    event, values = window.read()
    window.close()
    return event, values

def _settings_window():

    s = settings.recording
    layout = []
    ## todo display other setting
    #layout.append([sg.Text('Recording Settings')])
    layout.append(_group('General',
                         [_sg.Checkbox("Remote Control", s.remote_control,
                                       key="remote_control"),
                          _sg.Checkbox("Enter Filename Manually",
                                       s.ask_filename, key="ask_filename")]))

    layout.append([_sg.Frame('Sensor',
                             [_input_text_list("Device IDs", s.device_ids,
                                      key="device_ids"),
                     _input_text_list("Sensor Names", s.sensor_names,
                                      key="sensor_names")]
                             )])
    layout.append(_group('Record Forces & Torques',
                         [_sg.Checkbox("Fx", s.write_Fx, key="write_Fx"),
                          _sg.Checkbox("Fy", s.write_Fy, key="write_Fy"),
                          _sg.Checkbox("Fz", s.write_Fz, key="write_Fz"),
                          _sg.Checkbox("Tx", s.write_Tx, key="write_Tx"),
                          _sg.Checkbox("Ty", s.write_Ty, key="write_Ty"),
                          _sg.Checkbox("Tz", s.write_Tz, key="write_Tz")]))

    layout.append(_group('Trigger',
                         [_sg.Checkbox("Trigger1", s.write_trigger1, key="write_trigger1"),
                          _sg.Checkbox("Trigger2", s.write_trigger2, key="write_trigger2")]))

    layout.append([_sg.Save(), _sg.Cancel()])

    window =  _sg.Window('ForceGUI {}: Settings'.format(__version__), layout)
    event, values = window.read()

    d = settings.recording._asdict()
    if event=="Save":
        ## todo write settings

        for key in ("remote_control", "ask_filename",
                    "write_Fx", "write_Fy", "write_Fz",
                    "write_Tx", "write_Ty", "write_Tz",
                    "write_trigger1", "write_trigger2"):
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

        settings.set_recoding_setting(d)
        settings.save()

    window.close()
    return event

def run():
    _sg.theme('DarkAmber')  # please make your windows colorful

    while True:
        event, _ = _run_window()
        if event == "Settings":
            if _settings_window() == "Error":
                _sg.PopupError("Something is wrong with the settings.")
        else:
            break

    if event == "Start":
        _gui_run()
    else:
        pass
