# -*- coding: utf-8 -*-

"""
Openseame Object or the force DAQ remote control

(c) O. Lindemann

v0.9

"""

from . import remote_control as rc

from libopensesame.experiment import experiment
from libopensesame.exceptions import osexception
from openexp.canvas import canvas
from openexp.keyboard import keyboard

FORCE_SERVER_IP = "192.168.1.2"
WEAK, FINE, STRONG = [0, 1, 2]


class OpensesameDAQControl():

    def __init__(self, opensesame_experiment):
        """ OpenSesame clock and var"""

        if isinstance(opensesame_experiment, experiment):
            self._exp = opensesame_experiment
        else:
            raise osexception("opensesame_experiment needs to be an instance of " +\
                    "opensesame.experiment.experiment")

        self.clock = ExpyClock(self._exp.clock)
        self.subject_number = self._exp.var.get(u'subject_nr')
        self.experiment_name = self._exp.var.get(u'experiment_file').split('.')[0]
        self.udp = rc.init_udp_connection()
        self._exp.cleanup_functions.append(self.quit_recording)

    def __del__(self):
        self.quit_recording()

    def start(self, time_for_feedback=10):
        """ returns true if feedback is OK
        waits a particular time (in sec) for feedback and
        """

        self.udp.send(rc.Command.START)
        self.clock.reset_stopwatch()
        kbd = keyboard(self._exp)
        while True:
            rtn = self.udp.poll()
            kbd.get_key(timeout=0) # just for keyboard processing
            if rtn == rc.Command.FEEDBACK_STARTED:
                break
            if self.clock.stopwatch_time > time_for_feedback*1000:
                msg = "ERROR: Could not start recording <br/> Press key to quit"
                cnv = canvas(self._exp, text = msg)
                cnv.show()
                kbd.get_key()
                self._exp.end()
                exit()

        return True

    def stop(self):
        self.udp.send(rc.Command.QUIT)

    def quit_recording(self):
        if self.udp is not None:
            udp.send(rc.Command.QUIT)
        self.udp = None

    def pause(self, time_for_feedback=60 * 2, text_saving_time ="Please wait..."):
        """returns true if feedback is OK (that means data are saved)
        waits for a particular for feedback
        """

        self.udp.send(rc.Command.PAUSE)
        self.clock.reset_stopwatch()
        kbd = keyboard(self._exp)
        if text_saving_time != None:
            canvas(self._exp, text=text_saving_time).show()
        while True:
            rtn = self.udp.poll()
            kbd.get_key(timeout=1)
            if rtn == rc.Command.FEEDBACK_PAUSED:
                break
            if self.clock.stopwatch_time > time_for_feedback * 1000:
                return False

        if text_saving_time != None:
            canvas(self._exp).show()

        return True

    # make connection #
    def make_connection(self):
        """hand shake and filename,
        returns forceDAQ version
        """
        kbd = keyboard(self._exp)
        cnv = canvas(self._exp)

        cnv.text("Prepare force recording <br> press key if ready")
        cnv.show()
        kbd.get_key()
        canvas(self._exp).show()

        while not self.udp.connect_peer(FORCE_SERVER_IP):
            cnv = canvas(self._exp)
            cnv.text("ERROR while connecting to server <br> try again or Q to quit")
            cnv.show()
            key = kbd.get_key()
            if key[0] == u'q':
                msg = "Experiment quitted by user!"
                self.udp.send(rc.Command.QUIT)
                print(msg)
                self._exp.end()
                exit()
            canvas(self._exp).show()
            self.clock.wait(300)

        cnv = canvas(self._exp)
        cnv.text("Connected")
        cnv.show()
        self.clock.wait(500)
        self.udp.send(rc.Command.FILENAME + "{0}_{1}.csv".format(self.experiment_name,
                                                                 self.subject_number))
        rtn = self.udp.receive(5)  # paused
        if rtn is None:
            msg = "Force server not responding"
            cnv = canvas(self._exp, text = msg)
            cnv.show()
            kbd.get_key()
            self.udp.send(rc.Command.QUIT)
            print(msg)
            self._exp.end()
            exit()
        version = rc.get_data(rc.Command.GET_VERSION)
        cnv = canvas(self._exp)
        cnv.text("Connected <br> Version " + version)
        cnv.show()
        self.clock.wait(1000)
        return version

    def force_button_box_prepare(self):
        self.udp.clear_receive_buffer()
        self.udp.send(rc.Command.SET_LEVEL_CHANGE_DETECTION)
        self.udp.send(rc.Command.SET_LEVEL_CHANGE_DETECTION2)

    def force_button_box_check(self):
        """
        changes to level
        """
        evt, level = rc.poll_multiple_events([rc.Command.CHANGED_LEVEL,
                                              rc.Command.CHANGED_LEVEL2])
        if evt is not None:
            if evt == rc.Command.CHANGED_LEVEL:
                sensor = 1
            else:
                sensor = 2
            return (sensor, level)
        return (None, None)

    def force_button_box_wait(self, duration=None, minimum_level=-1):
        """
        returns if one of two sensors changes its level
        """

        self.clock.reset_stopwatch()
        kbd = keyboard(self._exp)
        last_key = None
        rt = None
        self.force_button_box_prepare()
        while not (duration is not None and self.clock.stopwatch_time > duration):
            sensor, level = self.force_button_box_check()
            if sensor is not None:
                if level >= minimum_level:
                    rt = self.clock.stopwatch_time
                    break
                else:
                    self.force_button_box_prepare()
                    sensor = None
            last_key, _ = kbd.get_key(timeout=0)
            if last_key is not None:
                break

        return sensor, level, rt, last_key

    def wait_no_button_pressed(self, feedback_stimulus_text=None, polling_intervall=500):
        """level detection needs to be switch on
        display feedback_stimulus (optional) if one button pressed
        """
        if rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0 or \
                        rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0:
            if feedback_stimulus_text is not None:
                cnv = canvas(self._exp)
                cnv.text(feedback_stimulus_text)
                cnv.show()
            kbd = keyboard(self._exp)
            while rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0 or \
                            rc.get_data(rc.Command.GET_THRESHOLD_LEVEL) > 0:
                kbd.get_key(timeout=polling_intervall)

    def set_thresholds(self, lower, upper):
        rc.set_force_thresholds(lower=lower, upper=upper)

    def hold_check(self, holding_time=3000,
                    left_pos=-200, right_pos=200, radius=50,
                    col_fine='gray',
                    col_too_low='green',
                    col_too_strong='red'):
        kbd = keyboard(self._exp)
        blank = canvas(self._exp)
        blank.show()

        self.udp.send("hold:test")
        self.clock.reset_stopwatch()
        prev_lv = None
        while True:
            self.udp.clear_receive_buffer()
            lv = [rc.get_data(rc.Command.GET_THRESHOLD_LEVEL),
                  rc.get_data(rc.Command.GET_THRESHOLD_LEVEL2)]
            if prev_lv!=lv:
                # level has changes
                self.clock.stopwatch_time()
                prev_lv = lv
                cnv = canvas(self._exp)
                for i, pos in enumerate([left_pos, right_pos]):
                    if lv[i] == WEAK:
                        cnv.circle(x=pos, y=0, r=radius, fill=True,
                                   color=col_too_low)
                    elif lv[i] == STRONG:
                        cnv.circle(x=pos, y=0, r=radius, fill=True,
                                   color=col_too_strong)
                    elif lv[i] == FINE:
                        cnv.circle(x=pos, y=0, r=radius, fill=True,
                                   color=col_fine)
                cnv.show()

            key, _ = kbd.get_key(timeout=0)
            if (lv == [FINE, FINE] and self.clock.stopwatch_time > holding_time) or\
                    (key is not None):
                break

        blank.show()


class ExpyClock():
    """Expyriment-like stopwatch based on Opensesame clock"""

    def __init__(self, opensesame_clock):
        self._clock = opensesame_clock
        self.reset_stopwatch()

    @property
    def time(self):
        return self._clock.time()

    @property
    def stopwatch_time(self):
        return self._clock.time() - self._start

    def reset_stopwatch(self):
        self._start = self._clock.time()

    def wait(self, waiting_time):
        return self._clock.sleep(waiting_time)
