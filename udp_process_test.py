__author__ = 'Oliver Lindemann'

from forceDAQ.misc.udp_connection import UDPConnectionProcess
from multiprocessing import Queue


if __name__=="__main__":
    receive_q = Queue()
    udp = UDPConnectionProcess(receive_q)

    udp.start()
    print "started"

    udp.event_is_connected.wait()
    print "connected"

    udp.stop()
