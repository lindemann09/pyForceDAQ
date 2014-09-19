# # Server

from force_recorder.udp_connection import UDPConnectionProcess, Queue

if __name__ == "__main__":
    receive_queue = Queue()
    udp_p = UDPConnectionProcess(receive_queue=receive_queue)
    udp_p.start()
    udp_p.event_polling.set() # start polling

    while True:
        data = receive_queue.get()
        print data
        if data is not None:
            udp_p.send_queue.put(data.string)
