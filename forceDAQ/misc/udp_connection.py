""" A lan connect class using udp

See COPYING file distributed along with the pyForceDAQ copyright and license terms.
"""

__author__ = "Oliver Lindemann <oliver@expyriment.org>"
__version__ = "0.3"

import os
from multiprocessing import Process, Event, Queue, sharedctypes
import atexit
from time import sleep, time
import socket

from timer import Timer, get_time
from forceDAQ.types import UDPData

if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                            0x8915, struct.pack('256s',
                                                                ifname[:15]))[20:24])


def get_lan_ip():
    # code bas on http://stackoverflow.com/questions/11735821/python-get-localhost-ip
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = [
            "eth0",
            "eth1",
            "eth2",
            "wlan0",
            "wlan1",
            "wifi0",
            "ath0",
            "ath1",
            "ppp0",
        ]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break
            except IOError:
                pass
    return ip


class UDPConnection(object):
    # todo: document the usage "connecting" "unconecting"
    COMMAND_CHAR = "$"
    CONNECT = COMMAND_CHAR + "connect"
    UNCONNECT = COMMAND_CHAR + "unconnect"
    COMMAND_REPLY = COMMAND_CHAR + "ok"
    PING = COMMAND_CHAR + "ping"

    def __init__(self, udp_port=5005):
        self.udp_port = udp_port

        self.socket = socket.socket(socket.AF_INET,  # Internet
                                    socket.SOCK_DGRAM)  # UDP
        self.my_ip = get_lan_ip()
        self.socket.bind((self.my_ip, self.udp_port))
        self.socket.setblocking(False)
        self.peer_ip = None

    def __str__(self):
        return "ip: {0} (port: {1}); peer: {2}".format(self.my_ip,
                                                       self.udp_port, self.peer_ip)

    def receive(self, timeout):
        """checks for received data and returns it

        In contrast to poll the function keep polling until timeout if no new
        data are available.

        timeout in seconds

        """

        t = get_time()
        while True:
            rtn = self.poll()
            if rtn is not None:
                return rtn
            if (get_time() - t) > timeout:
                return None

    def poll(self):
        """returns data or None if no data found
        process also commands

        if send is unkown input is ignored
        """

        try:
            data, sender = self.socket.recvfrom(1024)
        except:
            return None

        # process data
        if data == UDPConnection.CONNECT:
            #connection request
            self.peer_ip = sender[0]
            if not self.send(UDPConnection.COMMAND_REPLY):
                self.peer_ip = None
        elif sender[0] != self.peer_ip:
            return None  # ignore data
        elif data == UDPConnection.PING:
            self.send(UDPConnection.COMMAND_REPLY)
        elif data == self.UNCONNECT:
            self.unconnect_peer()
        return data

    def send(self, data, timeout=1.0):
        """returns if problems or not
        timeout in seconds (default = 1.0)
        return False if failed to send

        """
        if self.peer_ip is None:
            return False
        start = time()
        while time() - start < timeout:
            try:
                self.socket.sendto(data, (self.peer_ip, self.udp_port))
                # print "send:", data, self.peer_ip
                return True
            except:
                sleep(0.001)  # wait 1 ms
        return False

    def connect_peer(self, peer_ip, timeout=1):
        self.unconnect_peer()
        self.peer_ip = peer_ip
        if self.send(UDPConnection.CONNECT, timeout=timeout) and \
                self.wait_input(UDPConnection.COMMAND_REPLY, duration=timeout):
            return True
        self.peer_ip = None
        return False

    def wait_input(self, input_string, duration=1):
        """poll the connection and waits for a specific input"""
        start = time()
        while time() - start < duration:
            in_ = self.poll()
            if in_ == UDPConnection.COMMAND_REPLY:
                return True
        return False

    def unconnect_peer(self, timeout=1.0):
        self.send(UDPConnection.UNCONNECT)
        self.peer_ip = None

    @property
    def is_connected(self):
        return self.peer_ip is not None

    def ping(self, timeout=0.5):
        """returns boolean if suceeded and ping time"""
        if self.peer_ip == None:
            return (False, None)
        start = time()
        if self.send(UDPConnection.PING, timeout=timeout) and \
                self.wait_input(UDPConnection.COMMAND_REPLY, duration=timeout):
            return (True, ((time() - start) * 1000))
        return (False, None)

    def clear_receive_buffer(self):
        data = ""
        while data is not None:
            data = self.poll()

    def poll_last_data(self):
        """polls all data and returns only the last one
        return None if not data found"""
        rtn = None
        tmp = self.poll()
        while tmp is not None:
            rtn = tmp
            tmp = self.poll()
        return rtn


class UDPConnectionProcess(Process):
    """UDPConnectionProcess polls and writes to a data queue.

    Example::

        # Server that prints each input and echos it to the client
        # that is currently connected

        from udp_connection import UDPConnectionProcess, Queue

        receive_queue = Queue()
        udp_p = UDPConnectionProcess(receive_queue=receive_queue)
        udp_p.start()
        udp_p.event_polling.set() # start polling

        while True:
            data = receive_queue.get()
            print data
            if data is not None:
                udp_p.send_queue.put(data.string)

    Example::

        # connecting to a server
        # TODO
    """        # todo

    def __init__(self, sync_timer):
        """Initialize UDPConnectionProcess

        Parameters
        ----------
        receive_queue: multiprocessing.Queue
            the queue to which the received data should be put
        peer_ip : string
            the IP of the peer to which the connection should be established
        sync_clock : Clock
            the internal clock for timestamps will synchronized with this clock

        """ # todo

        super(UDPConnectionProcess, self).__init__()
        self._sync_timer = sync_timer
        self.receive_queue = Queue()
        self.send_queue = Queue()
        self.event_is_connected = Event()
        self._event_stop_request = Event()
        self._event_is_polling = Event()
        self._ip_address = sharedctypes.Array('c', 'xxx.xxx.xxx.xxx')

        atexit.register(self.stop)

    @property
    def ip_address(self):
        return self._ip_address.value

    def stop(self):
        self._event_stop_request.set()
        if self.is_alive():
            self.join()

    def pause(self):
        self._event_is_polling.clear()

    def start_polling(self):
        self._event_is_polling.set()

    def run(self):
        udp_connection = UDPConnection(udp_port=5005)
        print "UDP process started"
        print udp_connection
        self._ip_address.value = str(udp_connection.my_ip)
        self.start_polling()
        timer = Timer(self._sync_timer)
        while not self._event_stop_request.is_set():
            if not self._event_is_polling.is_set():
                self._event_is_polling.wait(timeout=0.1)
            else:
                data = udp_connection.poll()
                if data is not None:
                    self.receive_queue.put(UDPData(string=data,
                                                    time=timer.time))
                try:
                    send_data = self.send_queue.get_nowait()
                except:
                    send_data = None
                if send_data is not None:
                    udp_connection.send(send_data)

                # has connection changed?
                if self.event_is_connected.is_set() != udp_connection.is_connected:
                    if udp_connection.is_connected:
                        self.event_is_connected.set()
                    else:
                        self.event_is_connected.clear()

        udp_connection.unconnect_peer()
