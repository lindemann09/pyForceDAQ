""" A lan connect class using udp
"""

__author__ = "Oliver Lindemann <oliver@expyriment.org>"
__version__ = "0.1"

import os
from multiprocessing import Process, Event, Queue
import atexit

from clock import Clock
from time import sleep
import socket

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


class UDPData(object):
    """UDP Data object

    This object used for all received data

    """

    COMMAND_CHAR = "$"
    CONNECT_COMMAND = COMMAND_CHAR + "connect"
    UNCONNECT_COMMAND = COMMAND_CHAR + "unconnect"
    REPLY_COMMAND = COMMAND_CHAR + "ok"
    PING_COMMAND = COMMAND_CHAR + "ping"

    def __init__(self, string, sender, time=None):
        self.string = string
        self.sender = sender
        self.time = time

    def __str__(self):
        return "at {0} form {1}: '{2}' ".format(self.time, self.sender, self.string)

    @property
    def is_connect_command(self):
        return self.string == UDPData.CONNECT_COMMAND

    @property
    def is_unconnect_command(self):
        return self.string == UDPData.UNCONNECT_COMMAND

    @property
    def is_ping_command(self):
        return self.string == UDPData.PING_COMMAND


class UDPConnection(object):

    def __init__(self, udp_port=5005, timestamps=False, sync_clock=None):
        self.udp_port = udp_port

        self.socket = socket.socket(socket.AF_INET,  # Internet
                                    socket.SOCK_DGRAM)  # UDP
        self.my_ip = get_lan_ip()
        self.socket.bind((self.my_ip, self.udp_port))
        self.socket.setblocking(False)
        self.peer_ip = None
        self._clock = Clock(sync_clock=sync_clock)
        self.timestamps = timestamps

    def __str__(self):
        return "ip: {0} (port: {1}); peer: {2}".format(self.my_ip,
                                                       self.udp_port, self.peer_ip)

    def poll(self):
        """returns data or None if no data found
        process also commands

        if if send is unkown input is ignored
        """

        try:
            recv = self.socket.recvfrom(1024)
        except:
            return None

        if self.timestamps:
            data = UDPData(string=recv[0], sender=recv[1], time=self._clock.time)
        else:
            data = UDPData(string=recv[0], sender=recv[1])

        # process data
        if data.is_connect_command:
            #connection request
            self.peer_ip = data.sender
            if not self.send(UDPData.REPLY_COMMAND):
                self.peer_ip = None
            return None
        elif data.sender != self.peer_ip:
            return None  # ignore data
        elif data.is_ping_command:
            self.send(UDPData.REPLY_COMMAND)
            return None
        elif data.is_unconnect_command:
            self.unconnect_peer()
            return None

        return data

    def send(self, string, timeout=1.0):
        """returns if problems or not
        timeout in seconds (default = 1.0)
        return False if failed to send

        """
        if self.peer_ip is None:
            return False
        self._clock.reset_stopwatch()
        while self._clock.stopwatch_time < timeout * 1000:
            try:
                self.socket.sendto(string, (self.peer_ip, self.udp_port))
                # print "send:", data, self.peer_ip
                return True
            except:
                sleep(0.001)  # wait 1 ms
        return False

    def connect_peer(self, peer_ip, timeout=1.0):
        self.unconnect_peer()
        self.peer_ip = peer_ip
        if self.send(UDPData.CONNECT_COMMAND, timeout=timeout) and \
                self.wait_input(UDPData.REPLY_COMMAND, duration=timeout):
            return True
        self.peer_ip = None
        return False

    def wait_input(self, input_string, duration=1.0):
        """poll the connection and waits for a specific input"""
        self._clock.reset_stopwatch()
        while self._clock.stopwatch_time < duration * 1000:
            in_ = self.poll()
            if in_ == UDPData.REPLY_COMMAND:
                return True
        return False

    def unconnect_peer(self, timeout=1.0):
        self.send(UDPData.REPLY_COMMAND)
        self.peer_ip = None

    @property
    def is_connected(self):
        return self.peer_ip is not None

    def ping(self, timeout=0.5):
        """returns boolean if suceeded and ping time"""
        if self.peer_ip == None:
            return (False, None)
        self._clock.reset_stopwatch()
        if self.send(UDPData.PING_COMMAND, timeout=timeout) and \
                self.wait_input(input_string=UDPData.REPLY_COMMAND, duration=timeout):
            return (True, self._clock.stopwatch_time)
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

    def __init__(self, receive_queue, peer_ip=None, sync_clock=None):
        """UDPConnectionProcess

        Polls the UDPConnection and write the receive_queue
        Starting process automatically connects to peer and quits if connection failed.

        Examples
        -------

        # print each input and send it back
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

        """
        # todo: explain receiving data

        super(UDPConnectionProcess, self).__init__()
        self.receive_queue = receive_queue
        self.send_queue = Queue()
        self.event_polling = Event()
        self.event_is_connected = Event()

        self._event_stop_request = Event()
        self._peer_ip = peer_ip
        self._sync_clock = sync_clock

        atexit.register(self.stop)

    def connect(self, timeout=2.0):
        self.event_is_connected.clear()
        self.send_queue.put_nowait(UDPData.CONNECT_COMMAND)
        self.event_is_connected.wait(timeout=timeout)
        return self.event_is_connected.is_set()


    def stop(self):
        self._event_stop_request.set()


    def run(self):
        udp_connection = UDPConnection(udp_port=5005, timestamps=True,
                                       sync_clock=self._sync_clock)

        while not self._event_stop_request.is_set():
            if self.event_polling.is_set():
                data = udp_connection.poll()
                if data is not None:
                    self.receive_queue.put_nowait(data)

                try:
                    send_data = self.send_queue.get_nowait()
                except:
                    send_data = None

                if send_data is not None:
                    if not self.event_is_connected.is_set() and \
                            send_data == UDPData.CONNECT_COMMAND and \
                            self._peer_ip is not None:
                        udp_connection.connect_peer(peer_ip=self._peer_ip)
                    else:
                        udp_connection.send(send_data)

                if self.event_is_connected.is_set() != udp_connection.is_connected:
                    if udp_connection.is_connected:
                        self.event_is_connected.set()
                    else:
                        self.event_is_connected.clear()

            else:
                self.event_polling.wait(timeout=0.2)

        udp_connection.unconnect_peer()
