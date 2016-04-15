"""
import this module to have all relevant classes and function for the remote_control on your remote maschine
"""

__author__ = 'Oliver Lindemann'

import atexit

try:
    from cPickle import dumps, loads
except:
    from pickle import dumps, loads

from .base.types import Thresholds
from .base.types import GUIRemoteControlCommands as Command
from .base.udp_connection import UDPConnection

udp = None

def init_udp_connection():
    """init udp connecting afterwards udp connection is available via
        remote_control.udp

    REQUIRED BEFORE USING OTHER FUNCTIONS

    returns udp connection
    """
    global udp
    udp = UDPConnection()
    return udp

def quit():
    global udp
    if isinstance(udp, UDPConnection):
        udp.send(Command.QUIT)
    udp = None


atexit.register(quit)


def get_data(get_command):
    """Get data from the recording PC
    get_commands e.g.
        Command.GET_FZ or
        Command.GET_VERSION
        ....
    """

    udp.send(get_command)
    d = udp.receive(1)
    try:
        return loads(d.replace(Command.VALUE, ""))
    except:
        return None

def poll_event(event_type):
    """polling response minmax level
    event_tag:
        Command.RESPONSE_MINMAX or
        Command.CHANGED_LEVEL
        ....
    """
    rcv = udp.poll()
    if rcv is not None and rcv.startswith(event_type):
        x = loads(rcv.replace(event_type, ""))
        return x
    else:
        return None

def set_force_thresholds(lower, upper):
    thr = Thresholds([lower, upper])
    return udp.send(Command.SET_THRESHOLDS + dumps(thr))


def set_level_change_detection(sensor=1):
    if sensor==2:
        return udp.send(Command.SET_LEVEL_CHANGE_DETECTION2)
    else:
        return udp.send(Command.SET_LEVEL_CHANGE_DETECTION)
