# # Server
from forceDAQ.base.udp_connection import UDPConnectionProcess


udp_p = UDPConnectionProcess()
udp_p.start()
udp_p.start_polling()

connected = None
while True:
    data = udp_p.receive_queue.get()
    if data is not None:
        #udp_p.send_queue.put(data.string)
        print("received: {}".format(data.string))

    if udp_p.event_is_connected.is_set() != connected:
        connected = udp_p.event_is_connected.is_set()
        if connected:
            print("Server is connected")
        else:
            print("Server is unconnected")


udp_p.stop()
udp_p.join()
