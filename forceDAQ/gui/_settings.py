import os
import collections
import json

_GUISettings = collections.namedtuple('GUISettings', 'sampling_rate '
        'level_detection_parameter window_font moving_average_size '
        'screen_refresh_interval_indicator gui_screen_refresh_interval_plotter '
        'data_min_max plotter_pixel_min_max indicator_pixel_min_max plot_axis '
        'plot_data_indicator_for_single_sensor plot_data_plotter_for_single_sensor '
        'plot_data_indicator_for_two_sensors plot_data_plotter_for_two_sensors')

_RecordingSetting = collections.namedtuple('RecordingSetting',
          'device_name_prefix device_ids sensor_names remote_control '
          'ask_filename calibration_folder '
          ' zip_data write_Fx write_Fy '
          'write_Fz write_Tx write_Ty write_Tz  write_trigger1 '
          'write_trigger2  reverse_scaling convert_to_forces priority')


class GUISettings(object):

    def __init__(self, filename):

        # defaults
        self.gui = _GUISettings(
            sampling_rate = 1000,
            level_detection_parameter = "Fz",
            window_font = "freemono",
            moving_average_size = 5,
            screen_refresh_interval_indicator = 300,
            gui_screen_refresh_interval_plotter = 50,
            data_min_max = [-5, 30],
            plotter_pixel_min_max = [-250, 250],
            indicator_pixel_min_max = [-150, 150],
            plot_axis = False,
            plot_data_indicator_for_single_sensor = [(0, 0), (0, 1), (0, 2), (0, 3),
                                                     (0, 4), (0, 5)],  # sensor, parameter
            plot_data_plotter_for_single_sensor = [(0, 0), (0, 1), (0, 2)],
                              # plotter can't plot torques # TODO

            plot_data_indicator_for_two_sensors = [(0, 0), (0, 1), (0, 2), (1, 0),
                                                   (1, 1), (1, 2)],  # sensor,
                              # parameter
            plot_data_plotter_for_two_sensors = [(0, 2),
                                                 (1, 2)],
                              # plotter can't plot torques
        )
        self.gui_section = "GUI"

        self.recording = _RecordingSetting(device_name_prefix="Dev",
                       device_ids = [1],
                       sensor_names = ["FT30436"],
                       calibration_folder="C:\\Users\\Force\\Desktop\\calibration",
                       reverse_scaling = {1: ["Fz"], 2:["Fz"]},  # key: device_id, parameter. E.g.:if x & z dimension of sensor 1 and z dimension of sensor 2 has to be flipped use {1: ["Fx", "Fz"], 2: ["Fz"]}
                       remote_control=False, ask_filename= False, write_Fx=True,
                       write_Fy=True, write_Fz=True, write_Tx=False, write_Ty=False,
                       write_Tz=False, write_trigger1=True, write_trigger2=False,
                       zip_data=True, convert_to_forces=True,
                       priority='normal')
        self.recording_section = "Recording"

        self.filename = filename
        if os.path.isfile(self.filename):
            self.load()
        else:
            self.save() # defaults

    def _asdict(self):
        return {self.recording_section: self.recording._asdict(),
             self.gui_section: self.gui._asdict()}

    def set_gui_settings(self, gui_setting_dict):
        self.gui = _GUISettings(**gui_setting_dict)

    def set_recoding_setting(self, recording_setting_dict):
        self.recording = _RecordingSetting(**recording_setting_dict)

    def load(self, filename=None):
        if filename is not None:
            self.filename = filename

        with open(self.filename, 'r') as fl:
            d = json.load(fl)
        self.set_gui_settings(d[self.gui_section])
        self.set_recoding_setting(d[self.recording_section])

    def save(self):
        with open(self.filename, 'w') as fl:
            json.dump(self._asdict(), fl, indent=2)

    def recording_as_json(self):
        return json.dumps(self.recording._asdict())

settings = GUISettings(filename="pyForceDAQ.settings")