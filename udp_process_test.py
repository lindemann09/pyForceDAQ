__author__ = 'Oliver Lindemann'
from time import sleep
from forceDAQ.misc.udp_connection import UDPConnectionProcess
from multiprocessing import Queue


if __name__=="__main__":
    receive_q = Queue()
    udp = UDPConnectionProcess(receive_q)

    udp.start()
    print "started"

    udp.event_is_connected.wait()
    print "connected"
    goon = True
    while goon:
        udp.event_new_data_available.wait()
        udp.event_send_new_data.set()
        while udp.event_new_data_available.is_set(): # wait for new data are written
            sleep(0.001)
        #read data queue
        while True:
            try:
                data = receive_q.get_nowait()
                print data.data
                if data.data == "stop":
                    goon = False
            except:
                break

    udp.stop()
