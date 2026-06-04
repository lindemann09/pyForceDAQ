"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import logging
from pathlib import Path
from pickle import dumps
from typing import List

import numpy as np
import pygame
from expyriment import control, design, io, misc, stimuli

from .. import __version__ as forceDAQVersion
from .._lib.clock import wait_ms
from .._lib.data_recorder import DataRecorder
from .._lib.sensor_process import SensorProcess
from .._lib.settings import AppSettings, GUISettings, SensorSettings
from ..constants import DEFAULT_OUTPUT_FILENAME, DEFAULT_SETTINGS_FILE
from ._gui_status import GUIStatus
from ._layout import colours, get_pygame_rect, logo_text_line
from ._level_indicator import level_indicator
from ._plotter import PlotterThread

# eedback
COMMAND_STR = b"$"
RESPONSE_MINMAX = COMMAND_STR + b"xRM1"
RESPONSE_MINMAX2 = COMMAND_STR + b"xRM2"
CHANGED_LEVEL = COMMAND_STR + b"xCL1"
CHANGED_LEVEL2 = COMMAND_STR + b"xCL2"


def _main_loop(exp, recorder: DataRecorder, gs: GUISettings):
    """udp command:
    "start", "pause", "stop"
    "thresholds = [x,...]" : start level detection for Fz parameter and set threshold
    "thresholds stop" : stop level detection
    """

    indicator_grid = 70  # distance between indicator center
    plotter_width = 900
    plotter_position = (0, -30)

    s = GUIStatus(gui_settings=gs, recorder=recorder, screen_size=exp.screen.size)

    # plotter
    plotter_thread = None
    exp.keyboard.clear()

    while not s.quit_recording:  ######## process loop
        if s.pause_recording:
            wait_ms(100)

        ################################ process keyboard
        s.process_key(exp.keyboard.check(check_for_control_keys=False))

        ##############################  process udp
        udp = recorder.process_and_write_udp_events()
        while len(udp) > 0:
            s.process_udp_event(udp.pop(0))

        ########################### process new samples
        for x in s.check_new_samples():
            s.update_history(sensor=x)

            if s.thresholds is not None:
                # level change detection
                level_change, tmp = s.thresholds.get_level_change(
                    s.history[x].moving_average[gs.level_detection_parameter], channel=x
                )
                if level_change:
                    if x == 1:
                        recorder.udp.send_queue.put(CHANGED_LEVEL2 + dumps(tmp))  # type: ignore
                    else:
                        recorder.udp.send_queue.put(CHANGED_LEVEL + dumps(tmp))  # type: ignore

                # minmax detection
                tmp = s.thresholds.get_response_minmax(
                    s.history[x].moving_average[gs.level_detection_parameter], channel=x
                )
                if tmp is not None:
                    if x == 1:
                        recorder.udp.send_queue.put(RESPONSE_MINMAX2 + dumps(tmp))  # type: ignore
                    else:
                        recorder.udp.send_queue.put(RESPONSE_MINMAX + dumps(tmp))  # type: ignore

        ######################## show pause or recording screen
        if s.check_recording_status_change():
            if plotter_thread is not None:
                plotter_thread.join()
                plotter_thread = None

            if s.pause_recording:
                recorder.pause_saving(s.background)
                s.background.stimulus("Paused ('b' for baseline)").present()
            else:
                recorder.start_saving()
                s.set_start_recording_time()
                s.background.stimulus().present()

        ###########################
        ########################### plotting
        ###########################

        if s.check_refresh_required():  # do not give priority to visual output
            update_rects = []

            if s.check_thresholds_changed():
                _draw_plotter_thread_thresholds(
                    plotter_thread, s.thresholds, s.scaling_plotter
                )

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

                    if cnt == gs.level_detection_parameter:
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
                txt = stimuli.TextLine(
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
                txt = stimuli.TextLine(
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
                                lambda x: s.history[x[0]].moving_average[x[1]],
                                s.plot_data_plotter,
                            )
                        ),
                        dtype=float,
                    )
                else:
                    tmp = np.array(
                        list(
                            map(
                                lambda x: s.sensor_processes[x[0]].get_force(x[1]),
                                s.plot_data_plotter,
                            )
                        ),
                        dtype=float,
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
                    txt = stimuli.TextLine(
                        position=(xpos, ypos),
                        text=str(axis_labels[cnt]),
                        text_size=15,
                        text_colour=misc.constants.C_YELLOW,
                    )
                    txt.present(update=False, clear=False)
                    update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # counter
            pos = (-230, 250)
            stimuli.Canvas(
                position=pos, size=(400, 50), colour=misc.constants.C_BLACK
            ).present(update=False, clear=False)

            txt = stimuli.TextBox(
                position=pos,
                size=(400, 50),
                # background_colour=(30,30,30),
                text_size=15,
                text="n samples (total): {0} ({1} sec.)".format(
                    str(list(map(SensorProcess.get_saved_sample_cnt, s.sensor_processes)))[
                        1:-1
                    ],
                    s.recording_duration_in_sec,
                ),
                text_colour=misc.constants.C_YELLOW,
                text_justification=0,
            )
            txt.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(txt, exp.screen.size))

            # Infos
            pos = (200, 250)
            tmp = stimuli.Canvas(
                position=pos, size=(400, 50), colour=misc.constants.C_BLACK
            )
            tmp.present(update=False, clear=False)
            update_rects.append(get_pygame_rect(tmp, exp.screen.size))
            if s.thresholds is not None:
                if s.n_sensors > 1:
                    tmp = [
                        s.thresholds.get_level(s.level_detection_parameter_average(0)),
                        s.thresholds.get_level(s.level_detection_parameter_average(1)),
                    ]
                else:
                    tmp = s.thresholds.get_level(s.level_detection_parameter_average(0))
                txt = stimuli.TextBox(
                    position=pos,
                    size=(400, 50),
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

            # last_udp input
            if s.last_udp_data is not None:
                pos = (420, 250)
                stimuli.Canvas(
                    position=pos, size=(200, 30), colour=misc.constants.C_BLACK
                ).present(update=False, clear=False)
                txt = stimuli.TextBox(
                    position=pos,
                    size=(200, 30),
                    # background_colour=(30,30,30),
                    text_size=15,
                    text="UDP:" + str(s.last_udp_data),
                    text_colour=misc.constants.C_YELLOW,
                    text_justification=0,
                )
                txt.present(update=False, clear=False)
                update_rects.append(get_pygame_rect(txt, exp.screen.size))

            pygame.display.update(update_rects)
            # end plotting screen

        ##### end main  loop

    recorder.pause_saving(s.background)
    s.background.stimulus("Quitting").present()
    if plotter_thread is not None:
        plotter_thread.join()


def run_settings_file(settings_file: str | Path = ""):

    if isinstance(settings_file, str) and len(settings_file) < 2:
        # load default settings file if not specified
        settings_file = DEFAULT_SETTINGS_FILE

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
    logo_text_line("Initializing Force Recording").present()

    recorder = DataRecorder(
        recording_settings=rs,
        force_sensor_settings=sensor_settings,
        poll_udp_connection=False,  # FIXME remove UDP polling from recorder and put it in main loop
    )

    wait_ms(200)  # wait for lib init
    recorder.determine_biases(n_samples=500)

    if rs.save_data:
        if len(settings.output_filename) > 3:
            output_filename = settings.output_filename

        elif DEFAULT_OUTPUT_FILENAME is None:
            bkg = logo_text_line("")
            output_filename = io.TextInput("Filename", background_stimulus=bkg).get()
            output_filename = output_filename.replace(" ", "_")  # type: ignore

        else:
            output_filename = DEFAULT_OUTPUT_FILENAME

        recorder.open_data_file(output_filename, subdirectory="data", comment_line="")

    _main_loop(exp, recorder=recorder, gs=settings.gui)

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
