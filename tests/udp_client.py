from time import sleep

from force_recorder.udp_connection import UDPConnectionProcess, Queue

queue = Queue()
udp_p = UDPConnectionProcess(peer_ip="192.168.1.104", receive_queue=queue)
udp_p.start()
udp_p.event_polling.set() # start polling

if udp_p.connect():
    print "go"
    udp_p.send_queue.put("hello")
    sleep(0.2)
