__author__ = 'Oliver Lindemann'
from time import sleep
from forceDAQ.misc.udp_connection import UDPConnectionProcess


if __name__=="__main__":
    udp = UDPConnectionProcess(sync_timer=None)

    udp.start()
    print "started"

    udp.event_is_connected.wait()
    print "connected"
    goon = True
    while goon:
        try:
            udp_data = udp.receive_queue.get_nowait()
        except:
            udp_data = None

        if udp_data is not None:
            udp.send_queue.put(udp_data)
            print udp_data.data



    udp.stop()
