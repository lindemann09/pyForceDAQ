# # Server
from forceDAQ.base.udp_connection import UDPConnectionProcess, Queue
from forceDAQ.base.timer import Timer
from forceDAQ.base.udp_connection import UDPData


receive_queue = Queue()
udp_p = UDPConnectionProcess()
udp_p.start()
udp_p.start_polling()

while True:
    data = receive_queue.get()
    if data is not None:
        udp_p.send_queue.put(data.string)
        print(data.string)
