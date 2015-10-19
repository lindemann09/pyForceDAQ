# # Server
import time

import forceDAQ.udp_connection
import UDPConnection


udp_connection = UDPConnection()
print udp_connection

while True:
    data = udp_connection.poll()
    if data in [udp_connection.CONNECT, udp_connection.UNCONNECT]:
        print time.time(), data
        print udp_connection
    elif data == udp_connection.PING:
        print time.time(), data
    elif data is not None:
        udp_connection.send(data)
