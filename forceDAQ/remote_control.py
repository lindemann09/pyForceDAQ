__author__ = 'Oliver Lindemann'

from forceDAQ.misc.udp_connection import UDPConnection, UDPConnectionProcess

class GUIRemoteControlCommands(object):
    COMMAND_STR = "$cmd"
    FEEDBACK, START, PAUSE, QUIT, THRESHOLDS, PICKLED_VALUE, FILENAME, \
    GET_FX, GET_FY, GET_FZ, GET_TX, GET_TY, GET_TZ \
    = map(lambda x: "$cmd" + str(x), range(13))