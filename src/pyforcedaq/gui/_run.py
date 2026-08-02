"""
See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann"

import logging
import os
from pathlib import Path
from time import sleep

import numpy as np
import pygame
from expyriment import control, design, io, misc, stimuli

from .. import __version__ as forceDAQVersion
from ..constants import DEFAULT_OUTPUT_FILENAME
from ..lib.clock import wait_ms
from ..lib.data_recorder import DataRecorder
from ..lib.misc import Thresholds
from ..lib.settings import AppSettings, GUISettings, SensorSettings
from ._gui_status import GUIStatus
from ._layout import colours, get_pygame_rect, logo_text_line, make_text_line
from ._level_indicator import level_indicator
from ._plotter import PlotterThread

# Feedback

RESPONSE_MINMAX = "RM"
RESPONSE_MINMAX2 = "RM2"
CHANGED_LEVEL = "CL"
CHANGED_LEVEL2 = "CL2"

def _main_loop(exp, recorder: DataRecorder, gs: GUISettings, info_strings: list[str]):

    s = GUIStatus(gui_settings=gs, recorder=recorder, screen_size=exp.screen.size,
                  top_left_info=info_strings)

    # plotter
    plotter_thread = None
    exp.keyboard.clear()

    last_recording_status = None
    last_thresholds = None
    if recorder.lsl_events_stream is not None:
        recorder.lsl_events_stream.push_sample(["Recording started, " + forceDAQVersion])
    s.background.stimulus().present()

    while not s.quit_recording:  ######## process loop
        if s.pause_recording:
            wait_ms(100)

        ################################ process keyboard
        s.process_key(exp.keyboard.check(check_for_control_keys=False))

        ########################### process new samples
        for sensor_id in s.check_new_samples():
            # update sensor history
            s.history[sensor_id].append(s.sensor_processes[sensor_id].get_Fxyz())
            if len(s.threshold_list) > 0:
                # level change detection
                f = s.history[sensor_id].buffer_mean()[s.force_id_level_detect]
                level_change = s.threshold_list[sensor_id].process(f) # type: ignore
                if level_change:
                    lvl = s.threshold_list[sensor_id].current_level
                    if sensor_id == 1:
                        resp = f"{CHANGED_LEVEL}-{lvl}"
                    else:
                        resp = f"{CHANGED_LEVEL2}-{lvl}"
                    if recorder.lsl_events_stream is not None:
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

        ########################### plotting
        if s.check_refresh_required():  # do not give priority to visual output
            thr = s.threshold_list[0] if len(s.threshold_list) > 0 else None
            if thr != last_thresholds:
                # thresholds have changed
                _draw_plotter_thread_thresholds(
                    plotter_thread, thr, s.scaling_plotter
                )
                last_thresholds = thr

            if s.plot_indicator:
                ### plot_indicator
                if plotter_thread is not None:
                    # kill plotter thread if indicator is used
                    plotter_thread.join()
                    plotter_thread = None
                update_rects = _update_indicator_plotter(status=s,
                                                         exp_screen_size=exp.screen.size,
                                                         indicator_grid=70)
            else:
                ### plotter
                if plotter_thread is None:
                    plotter_thread = _make_plotter_thread(status=s, gs=gs,
                                                          plotter_width=900,
                                                          plotter_position=(0, -30))
                update_rects = _update_plotter(
                    plotter_thread, status=s,
                    plotter_width=900,
                    plotter_position=(0, -30),
                    exp_screen_size=exp.screen.size)

            update_rects = _draw_plotter_texts(update_rects, status=s, exp_screen_size=exp.screen.size)

            pygame.display.update(update_rects)
            # end plotting screen

        ##### end main  loop

    recorder.pause_saving()
    if recorder.lsl_events_stream is not None:
        recorder.lsl_events_stream.push_sample(["Recording stopped"])
    s.background.stimulus("Quitting").present()
    if plotter_thread is not None:
        plotter_thread.join()


def run_settings_file(settings_file: str | Path = ""):
    return run(AppSettings(settings_file, create_if_not_exists=False))


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
    working_dir = settings.file.parent
    logging.info("New Recording with forceDAQ %s", forceDAQVersion)
    logging.info("Sensors %s", [sensor["calibration_file_name"] for sensor in rs.sensors])
    logging.info("Settings %s", settings.recording_as_json)

    sensor_settings: list[SensorSettings] = rs.get_sensor_settings(working_dir)

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

        filepath = rs.absolute_path_data(working_dir) / output_filename
        recorder.open_data_file(filepath, comment_line="")

    sleep(show_logo_time)

    _main_loop(exp, recorder=recorder, gs=settings.gui,
               info_strings=[f"{settings.file.name}"])

    recorder.quit()
    control.end()
    return True


def _update_indicator_plotter(
                              status:GUIStatus,
                             exp_screen_size:tuple, indicator_grid = 70) -> list[pygame.Rect]:
    """update the indicator or plotter display
        indicator_grid = distance between indicator center
    """
    ############################################  plot_indicator
    update_rects = []
    ## indicator
    for cnt, vals in enumerate(status.plot_data_indicator):
        sensor_id, force_id = vals
        force = status.sensor_processes[sensor_id].get_force(force_id)

        x_pos = (
            (-3 * indicator_grid)
            + (cnt * indicator_grid)
            + 0.5 * indicator_grid
        )

        if force_id == status.force_id_level_detect and len(status.threshold_list) > 0:
            thr = status.threshold_list[sensor_id]
        else:
            thr = None

        li = level_indicator(
            value=force,
            text=status.plot_data_indicator_names[cnt],
            scaling=status.scaling_indicator,
            width=50,
            position=(x_pos, 0),
            thresholds=thr,
        )
        li.present(update=False, clear=False)
        update_rects.append(get_pygame_rect(li, exp_screen_size))

    # line
    zero = status.scaling_indicator.data2pixel(status.scaling_indicator.trim(0))
    rect = stimuli.Line(
        start_point=(-200, zero),
        end_point=(200, zero),
        line_width=1,
        colour=misc.constants.C_YELLOW,
    )
    rect.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(rect, exp_screen_size))

    # axis labels
    pos = (-220, -145)
    stimuli.Canvas(
        position=pos, size=(30, 20), colour=misc.constants.C_BLACK
    ).present(update=False, clear=False)
    txt = make_text_line(
        position=pos,
        text=str(status.scaling_indicator.min),
        text_size=15,
        text_colour=misc.constants.C_YELLOW,
    )
    txt.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(txt, exp_screen_size))
    pos = (-220, 145)
    stimuli.Canvas(
        position=pos, size=(30, 20), colour=misc.constants.C_BLACK
    ).present(update=False, clear=False)
    txt = make_text_line(
        position=pos,
        text=str(status.scaling_indicator.max),
        text_size=15,
        text_colour=misc.constants.C_YELLOW,
    )
    txt.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(txt, exp_screen_size))
    # end indicator

    stimuli.Canvas(
        position=(-250, 200), size=(200, 50), colour=misc.constants.C_BLACK
    ).present(update=False, clear=False)
    txt = stimuli.TextBox(
        text=str(status.sensor_info_str),
        # background_colour=(30,30,30),
        size=(200, 50),
        text_size=15,
        position=(-250, 200),
        text_colour=misc.constants.C_YELLOW,
        text_justification=0,
    )
    txt.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(txt, exp_screen_size))
    return update_rects


def _make_plotter_thread(status:GUIStatus, gs:GUISettings, plotter_width:int , plotter_position:tuple) -> PlotterThread:

    plotter_thread = PlotterThread(
        n_data_rows=len(status.plot_data_plotter),
        data_row_colours=colours[: len(status.plot_data_plotter)],
        y_range=[
            status.scaling_plotter.pixel_min,
            status.scaling_plotter.pixel_max,
        ],
        width=plotter_width,
        position=plotter_position,
        background_colour=[10, 10, 10],
        axis_colour=misc.constants.C_YELLOW,
    )
    plotter_thread.start()

    if gs.plot_axis:
        plotter_thread.set_horizontal_lines(
            y_values=[status.scaling_plotter.data2pixel(0)]
        )

    if len(status.threshold_list) > 0:
        plotter_thread.set_horizontal_lines(
            y_values=status.scaling_plotter.data2pixel(
                np.array(status.threshold_list[0].thresholds)
            )
        )
    return plotter_thread

def _update_plotter(plotter_thread:PlotterThread,
                    status:GUIStatus,
                    plotter_width:int ,
                    plotter_position:tuple,
                    exp_screen_size:tuple) -> list[pygame.Rect]:
    ############################################  plotter
    update_rects = []

    if status.clear_screen:
        plotter_thread.clear_area()
        status.clear_screen = False

    lvl = np.array([status.sensor_processes[x[0]].get_force(x[1])
                        for x in status.plot_data_plotter],
                    dtype=np.float64)

    if len(status.threshold_list)>0:
        is_detecting = [thr.has_level() for thr in status.threshold_list]
        point_marker = bool(np.any(is_detecting))
    else:
        point_marker = False

    plotter_thread.add_values(
        values=status.scaling_plotter.data2pixel(lvl),
        set_marker=status.set_marker,
        set_point_marker=point_marker,
    )
    status.set_marker = False

    update_rects.append(plotter_thread.get_plotter_rect(exp_screen_size))

    # axis labels
    axis_labels = (
        int(status.scaling_plotter.min),
        int(status.scaling_plotter.max),
        0,
    )
    xpos = plotter_position[0] - (plotter_width / 2) - 20
    for cnt, ypos in enumerate(
        (
            plotter_position[1] + status.scaling_plotter.pixel_min + 10,
            plotter_position[1] + status.scaling_plotter.pixel_max - 10,
            plotter_position[1] + status.scaling_plotter.data2pixel(0),
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
        update_rects.append(get_pygame_rect(txt, exp_screen_size))

    return update_rects

def _draw_plotter_texts(update_rects:list[pygame.Rect], status:GUIStatus,
                        exp_screen_size:tuple) -> list[pygame.Rect]:

    pos = (-270, 240)
    stimuli.Canvas(
        position=pos, size=(400, 20), colour=misc.constants.C_BLACK
    ).present(update=False, clear=False)

    sample_cnt = [x.get_total_sample_cnt() for x in status.sensor_processes]
    txt = stimuli.TextBox(
        position=pos,
        size=(400, 20),
        # background_colour=(30,30,30),
        text_size=15,
        text = f"n samples (total): {sample_cnt}",
        text_colour=misc.constants.C_YELLOW,
        text_justification=0,
    )
    txt.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(txt, exp_screen_size))

    # Sensor info
    pos = (200, 250)
    lvl = stimuli.Canvas(
        position=pos, size=(600, 50), colour=misc.constants.C_BLACK
    )
    lvl.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(lvl, exp_screen_size))

    # print level detection
    if len(status.threshold_list) > 0:
        thr = status.threshold_list[0].thresholds
        lvl = [x.current_level for x in status.threshold_list]
        txt = stimuli.TextBox(
            position=pos,
            size=(600, 50),
            text_size=15,
            text=f"T: {thr} L: {lvl}",
            text_colour=misc.constants.C_YELLOW,
            text_justification=0,
        )
        txt.present(update=False, clear=False)

    pos = (400, 250)
    lvl = stimuli.Canvas(
        position=pos, size=(400, 50), colour=misc.constants.C_BLACK
    )
    lvl.present(update=False, clear=False)
    update_rects.append(get_pygame_rect(lvl, exp_screen_size))
    return update_rects


#### helper
def _draw_plotter_thread_thresholds(plotter_thread, thresholds: Thresholds | None, scaling):
    if plotter_thread is not None:
        if thresholds is not None:
            plotter_thread.set_horizontal_lines(
                y_values=scaling.data2pixel(np.array(thresholds.thresholds))
            )
        else:
            plotter_thread.set_horizontal_lines(y_values=None)