"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import logging
import os
from pathlib import Path
from time import sleep
from typing import List

import numpy as np
import pygame
from expyriment import control, design, io, misc, stimuli

from .. import __version__ as forceDAQVersion
from .._lib.clock import wait_ms
from .._lib.data_recorder import DataRecorder
from .._lib.sensor_process import SensorProcess
from .._lib.settings import AppSettings, GUISettings, SensorSettings
from .._lib.types import ForceSensorData
from ..constants import DEFAULT_OUTPUT_FILENAME
from ._gui_status import GUIStatus
from ._layout import colours, get_pygame_rect, logo_text_line, make_text_line
from ._level_indicator import level_indicator
from ._plotter import PlotterThread

# Feedback

RESPONSE_MINMAX = "RM"
RESPONSE_MINMAX2 = "RM2"
CHANGED_LEVEL = "CL"
CHANGED_LEVEL2 = "CL2"

def _main_loop(exp, recorder: DataRecorder, gs: GUISettings, info_strings: List[str]):

    indicator_grid = 70  # distance between indicator center
    plotter_width = 900
    plotter_position = (0, -30)

    s = GUIStatus(gui_settings=gs, recorder=recorder, screen_size=exp.screen.size,
                  top_left_info=info_strings)

    # plotter
    plotter_thread = None
    exp.keyboard.clear()

    last_recording_status = None
    last_thresholds = None
    recorder.lsl_events_stream.push_sample(["Recording started, " + forceDAQVersion])
    s.background.stimulus().present()

    while not s.quit_recording:  ######## process loop
        if s.pause_recording:
            wait_ms(100)

        ################################ process keyboard
        s.process_key(exp.keyboard.check(check_for_control_keys=False))

        ########################### process new samples
        for x in s.check_new_samples():
            s.update_history(sensor=x)

            if s.thresholds is not None and isinstance(s.force_id_level_detect, int):
                # level change detection
                level_change, tmp = s.thresholds.get_level_change(
                    s.history[x].moving_average(s.force_id_level_detect), channel=x
                )
                if level_change:
                    if x == 1:
                        resp = f"{CHANGED_LEVEL}-{tmp}"
                    else:
                        resp = f"{CHANGED_LEVEL2}-{tmp}"
                    recorder.lsl_events_stream.push_sample([resp])

                ## minmax detection FIXME needs to call first  "set_response_minmax_detection"
                # tmp = s.thresholds.get_response_minmax(
                #     s.history[x].moving_average(s.force_id_level_detect), channel=x
                # )
                # if tmp[0] is not None:
                #     if x == 1:
                #         resp = f"{RESPONSE_MINMAX}-{tmp}"
                #     else:
                #         resp = f"{RESPONSE_MINMAX2}-{tmp}"
                #     recorder.lsl_events_stream.push_sample([resp])

        ######################## show pause or recording screen
        if s.pause_recording != last_recording_status:
            last_recording_status = s.pause_recording
            if s.pause_recording:
                recorder.pause_saving()
            else:
                recorder.start_saving()

        ###########################
        ########################### plotting
        ###########################

        if s.check_refresh_required():  # do not give priority to visual output
            update_rects = []

            if s.thresholds != last_thresholds:
                # thresholds have changed
                _draw_plotter_thread_thresholds(
                    plotter_thread, s.thresholds, s.scaling_plotter
                )
                last_thresholds = s.thresholds

            if s.plot_indicator:
                ############################################  plot_indicator
                if plotter_thread is not None:
                    plotter_thread.join()
                    plotter_thread = None

                ## indicator
                force_data_array = list(
                    map(
                        lambda x: s.sensor_processes[x[0]].get_force(x[1]),
                        s.plot_data_indicator,
                    )
                )

                for cnt in range(6):
                    x_pos = (
                        (-3 * indicator_grid)
                        + (cnt * indicator_grid)
                        + 0.5 * indicator_grid
                    )

                    if cnt == s.force_id_level_detect:
                        thr = s.thresholds
                    else:
                        thr = None
                    li = level_indicator(
                        value=force_data_array[cnt],
                        text=s.plot_data_indicator_names[cnt],
                        scaling=s.scaling_indicator,
                        width=50,
                        position=(x_pos, 0),
                        thresholds=thr,
                    )
                    li.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(li, exp.screen.size))

                # line
                zero = s.scaling_indicator.data2pixel(s.scaling_indicator.trim(0))
                rect = stimuli.Line(
                    start_point=(-200, zero),
                    end_point=(200, zero),
                    line_width=1,
                    colour=misc.constants.C_YELLOW,
                )
                rect.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(rect, exp.screen.size))

                # axis labels
                pos = (-220, -145)
                stimuli.Canvas(
                    position=pos, size=(30, 20), colour=misc.constants.C_BLACK
                ).present(update=False, clear=False)
                txt = make_text_line(
                    position=pos,
                    text=str(s.scaling_indicator.min),
                    text_size=15,
                    text_colour=misc.constants.C_YELLOW,
                )
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                pos = (-220, 145)
                stimuli.Canvas(
                    position=pos, size=(30, 20), colour=misc.constants.C_BLACK
                ).present(update=False, clear=False)
                txt = make_text_line(
                    position=pos,
                    text=str(s.scaling_indicator.max),
                    text_size=15,
                    text_colour=misc.constants.C_YELLOW,
                )
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
                # end indicator

                stimuli.Canvas(
                    position=(-250, 200), size=(200, 50), colour=misc.constants.C_BLACK
                ).present(update=False, clear=False)
                txt = stimuli.TextBox(
                    text=str(s.sensor_info_str),
                    # background_colour=(30,30,30),
                    size=(200, 50),
                    text_size=15,
                    position=(-250, 200),
                    text_colour=misc.constants.C_YELLOW,
                    text_justification=0,
                )
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))
            else:
                ############################################  plotter
                if plotter_thread is None:
                    plotter_thread = PlotterThread(
                        n_data_rows=len(s.plot_data_plotter),
                        data_row_colours=colours[: len(s.plot_data_plotter)],
                        y_range=[
                            s.scaling_plotter.pixel_min,
                            s.scaling_plotter.pixel_max,
                        ],
                        width=plotter_width,
                        position=plotter_position,
                        background_colour=[10, 10, 10],
                        axis_colour=misc.constants.C_YELLOW,
                    )
                    plotter_thread.start()

                    if gs.plot_axis:
                        plotter_thread.set_horizontal_lines(
                            y_values=[s.scaling_plotter.data2pixel(0)]
                        )

                    if s.thresholds is not None:
                        plotter_thread.set_horizontal_lines(
                            y_values=s.scaling_plotter.data2pixel(
                                np.array(s.thresholds.thresholds)
                            )
                        )

                if s.clear_screen:
                    plotter_thread.clear_area()
                    s.clear_screen = False

                if s.plot_filtered:
                    tmp = np.array(
                        list(
                            map(
                                lambda x: s.history[x[0]].moving_average(x[1]),
                                s.plot_data_plotter,
                            )
                        ),
                        dtype=np.float64,
                    )
                else:
                    tmp = np.array(
                        list(
                            map(
                                lambda x: s.sensor_processes[x[0]].get_force(x[1]),
                                s.plot_data_plotter,
                            )
                        ),
                        dtype=np.float64,
                    )

                if s.thresholds is not None:
                    point_marker = s.thresholds.is_detecting_anything()
                else:
                    point_marker = False

                plotter_thread.add_values(
                    values=s.scaling_plotter.data2pixel(tmp),
                    set_marker=s.set_marker,
                    set_point_marker=point_marker,
                )
                s.set_marker = False

                update_rects.append(plotter_thread.get_plotter_rect(exp.screen.size))

                # axis labels
                axis_labels = (
                    int(s.scaling_plotter.min),
                    int(s.scaling_plotter.max),
                    0,
                )
                xpos = plotter_position[0] - (plotter_width / 2) - 20
                for cnt, ypos in enumerate(
                    (
                        plotter_position[1] + s.scaling_plotter.pixel_min + 10,
                        plotter_position[1] + s.scaling_plotter.pixel_max - 10,
                        plotter_position[1] + s.scaling_plotter.data2pixel(0),
                    )
                ):
                    stimuli.Canvas(
                        position=(xpos, ypos),
                        size=(50, 30),
                        colour=misc.constants.C_BLACK,
                    ).present(update=False, clear=False)
                    txt = make_text_line(
                        position=(xpos, ypos),
                        text=str(axis_labels[cnt]),
                        text_size=15,
                        text_colour=misc.constants.C_YELLOW,
                    )
                    txt.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # counter
            pos = (-270, 240)

            stimuli.Canvas(
                position=pos, size=(400, 20), colour=misc.constants.C_BLACK
            ).present(update=False, clear=False)

            txt = stimuli.TextBox(
                position=pos,
                size=(400, 20),
                # background_colour=(30,30,30),
                text_size=15,
                text="n samples (total): {0}".format(
                    str(list(map(SensorProcess.get_saved_sample_cnt, s.sensor_processes)))[
                        1:-1]),
                text_colour=misc.constants.C_YELLOW,
                text_justification=0,
            )
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # Sensor info
            pos = (200, 250)
            tmp = stimuli.Canvas(
                position=pos, size=(600, 50), colour=misc.constants.C_BLACK
            )
            tmp.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))
            if s.thresholds is not None:
                if s.n_sensors > 1:
                    tmp = [
                        s.thresholds.get_level(s.get_average_level_detection_parameter(0)),
                        s.thresholds.get_level(s.get_average_level_detection_parameter(1)),
                    ]
                else:
                    tmp = s.thresholds.get_level(s.get_average_level_detection_parameter(0))


                txt = stimuli.TextBox(
                    position=pos,
                    size=(600, 50),
                    text_size=15,
                    text="T: {0} L: {1}".format(s.thresholds, tmp),
                    text_colour=misc.constants.C_YELLOW,
                    text_justification=0,
                )
                txt.present(update=False, clear=False)

            pos = (400, 250)
            tmp = stimuli.Canvas(
                position=pos, size=(400, 50), colour=misc.constants.C_BLACK
            )
            tmp.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))
            if s.plot_filtered:
                txt = stimuli.TextBox(
                    position=pos,
                    size=(400, 50),
                    text_size=15,
                    text="Filtered data!",
                    text_colour=misc.constants.C_YELLOW,
                    text_justification=0,
                )
                txt.present(update=False, clear=False)

            pygame.display.update(update_rects)
            # end plotting screen

        ##### end main  loop

    recorder.pause_saving()
    recorder.lsl_events_stream.push_sample(["Recording stopped"])
    s.background.stimulus("Quitting").present()
    if plotter_thread is not None:
        plotter_thread.join()


def run_settings_file(settings_file: str | Path = ""):
    return run(AppSettings(settings_file))


def run(settings: AppSettings):
    """start recording with specified settings

     reverse scaling: dictionary with rescaling (see SensorSetting)
                 key: device_label, value: list of parameter names (e.g., ["Fx"])

    polling_priority has to be types.PRIORITY_{HIGH}, {REALTIME} or
                         {NORMAL} or None

     returns False only if quited by key while waiting for remote control
    """
    #
    rs = settings.recording
    logging.info("New Recording with forceDAQ %s", forceDAQVersion)
    logging.info("Sensors %s", rs.calibration_files)
    logging.info("Settings %s", settings.recording_as_json)

    if not isinstance(rs.device_labels, (list, tuple)):
        rs.device_labels = [rs.device_labels]
    if not isinstance(rs.calibration_files, (list, tuple)):
        rs.calibration_files = [rs.calibration_files]

    sensor_settings: List[SensorSettings] = rs.sensor_settings_list()

    # expyriment
    control.defaults.initialise_delay = 0
    control.defaults.window_mode = True
    control.defaults.window_size = (1000, 700)
    control.defaults.fast_quit = True
    control.defaults.opengl = False
    control.defaults.event_logging = 0
    control.defaults.audiosystem_autostart = False
    exp = design.Experiment(text_font=settings.gui.window_font)
    exp.set_log_level(0)

    control.initialize(exp)
    exp.mouse.show_cursor()  # type: ignore #
    pygame.display.set_caption(f"pyforceDAQ {forceDAQVersion}")

    icon_path = os.path.join(os.path.dirname(__file__), "rf_icon.png")
    pygame.display.set_icon(pygame.image.load(icon_path))

    logo_text_line("Initializing Force Recording").present()
    show_logo_time = 0.5
    recorder = DataRecorder(
        recording_settings=rs,
        force_sensor_settings=sensor_settings
    )

    if rs.save_data:
        if len(settings.output_filename) > 3:
            output_filename = settings.output_filename

        elif DEFAULT_OUTPUT_FILENAME is None:
            bkg = logo_text_line("")
            output_filename = io.TextInput("Filename", background_stimulus=bkg).get()
            output_filename = output_filename.replace(" ", "_")  # type: ignore
            show_logo_time  = 0
        else:
            output_filename = DEFAULT_OUTPUT_FILENAME

        recorder.open_data_file(output_filename, subdirectory="data", comment_line="")

    sleep(show_logo_time)

    _main_loop(exp, recorder=recorder, gs=settings.gui,
               info_strings=[f"{settings.filepath.name}"])

    recorder.quit()
    control.end()
    return True


#### helper
def _draw_plotter_thread_thresholds(plotter_thread, thresholds, scaling):
    if plotter_thread is not None:
        if thresholds is not None:
            plotter_thread.set_horizontal_lines(
                y_values=scaling.data2pixel(np.array(thresholds.thresholds))
            )
        else:
            plotter_thread.set_horizontal_lines(y_values=None)


def _strlist_append(prefix, strlist):
    return list(map(lambda x: prefix + x, strlist))
