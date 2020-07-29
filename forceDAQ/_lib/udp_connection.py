""" A lan connect class using udp
"""

__author__ = "Oliver Lindemann <oliver@expyriment.org>"
__version__ = "0.5"

import atexit
import os
import socket
from multiprocessing import Process, Event, Queue
import logging

from .._lib.types import UDPData
from .._lib.polling_time_profile import PollingTimeProfile
from .._lib.process_priority_manager import get_priority
from .timer import Timer, app_timer, get_time_ms
from .. import PYTHON3

def get_lan_ip():
    if os.name != "nt":
        # linux
        from subprocess import check_output
        rtn = check_output("hostname -I".split(" "))
        if PYTHON3:
            rtn = rtn.decode()
        rtn = rtn.split(" ")
        return rtn[0].strip()

    else:
        # windows
        # code bas on http://stackoverflow.com/questions/11735821/python-get-localhost-ip
        return socket.gethostbyname(socket.gethostname())


class UDPConnection(object):
    # todo: document the usage "connecting" "unconnecting"
    COMMAND_CHAR = b"$"
    CONNECT = COMMAND_CHAR + b"connect"
    UNCONNECT = COMMAND_CHAR + b"unconnect"
    COMMAND_REPLY = COMMAND_CHAR + b"ok"
    PING = COMMAND_CHAR + b"ping"

    MY_IP = get_lan_ip()

    def __init__(self, udp_port=5005):
        self.udp_port = udp_port

        self._socket = socket.socket(socket.AF_INET,  # Internet
                                     socket.SOCK_DGRAM)  # UDP
        self._socket.bind((UDPConnection.MY_IP, self.udp_port))
        self._socket.setblocking(False)
        self.peer_ip = None
        self.timer = Timer(sync_timer=app_timer) # own timer, because often
        # used in own process

    @property
    def my_ip(self):
        return UDPConnection.MY_IP

    def __str__(self):
        return "ip: {0} (port: {1}); peer: {2}".format(UDPConnection.MY_IP,
                                                       self.udp_port, self.peer_ip)

    def receive(self, timeout):
        """checks for received data and returns it

        In contrast to poll the function keep polling until timeout if no new
        data are available.

        timeout in seconds

        """

        t = get_time_ms()
        timeout_ms = int(timeout*1000)
        while True:
            rtn = self.poll()
            if rtn is not None:
                #print("UDP receive: {0}".format(rtn))
                return rtn
            if (get_time_ms() - t) > timeout_ms:
                return None

    def poll(self):
        """returns data (bytes) or None if no data found
        process also commands

        if send is unkown input is ignored
        """

        try:
            data, sender = self._socket.recvfrom(1024)
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
        timeout_ms = int(timeout*1000)
        if self.peer_ip is None:
            return False
        start = get_time_ms()
        if PYTHON3 and isinstance(data, str):
            data = data.encode() # force to byte

        while get_time_ms() - start < timeout_ms:
            try:
                self._socket.sendto(data, (self.peer_ip, self.udp_port))
                #print("UDP send: {0}".format(data))
                return True
            except:
                pass
        return False

    def connect_peer(self, peer_ip, timeout=1.0):

        self.unconnect_peer()
        self.peer_ip = peer_ip
        if self.send(UDPConnection.CONNECT, timeout=timeout) and \
                self.wait_input(UDPConnection.COMMAND_REPLY, duration=timeout):
            return True
        self.peer_ip = None
        return False

    def wait_input(self, input_string, duration=1.0):
        """poll the connection and waits for a specific input"""
        start = get_time_ms()
        duration_ms = int(duration*1000)
        while get_time_ms() - start < duration_ms:
            in_ = self.poll()
            if in_ == input_string:
                return True
        return False

    def unconnect_peer(self, timeout=1.0):
        self.send(UDPConnection.UNCONNECT, timeout=timeout)
        self.peer_ip = None

    @property
    def is_connected(self):
        return self.peer_ip is not None

    def ping(self, timeout=0.5):
        """returns boolean if succeeded and ping time in ms"""

        if self.peer_ip == None:
            return False, None
        start = get_time_ms()
        if self.send(UDPConnection.PING, timeout=timeout) and \
                self.wait_input(UDPConnection.COMMAND_REPLY, duration=timeout):
            return True, get_time_ms() - start
        return False, None

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
            print(data)
            if data is not None:
                udp_p.send_queue.put(data.string)

    Example::

        # connecting to a server
    """        # todo docu

    def __init__(self, event_trigger = (),
                 event_ignore_tag = None):
        """Initialize UDPConnectionProcess

        Parameters
        ----------
        receive_queue: multiprocessing.Queue
            the queue to which the received data should be put

        peer_ip : string
            the IP of the peer to which the connection should be established

        sync_clock : Clock
            the internal clock for timestamps will synchronized with this clock

        event_trigger: multiprocessing.Event() (or list of..)
            event trigger(s) to be set. If Udp event is received and it is not a
            command to set this event (typical of sensor recording processes).

        event_ignore_tag:
            udp data that start with this tag will be ignored for event triggering

        """ # todo docu

        super(UDPConnectionProcess, self).__init__()

        self.receive_queue = Queue()
        self.send_queue = Queue()
        self.event_is_connected = Event()
        self._event_quit_request = Event()
        self._event_is_polling = Event()
        self._event_ignore_tag = event_ignore_tag

        if isinstance(event_trigger, type(Event)  ):
            event_trigger = (event_trigger)
        try:
            self._event_trigger = tuple(event_trigger)
        except:
            self._event_trigger = ()

        atexit.register(self.quit)

    @property
    def my_ip(self):
        return UDPConnection.MY_IP

    def quit(self):
        self._event_quit_request.set()
        if self.is_alive():
            self.join()

    def pause(self):
        self._event_is_polling.clear()

    def start_polling(self):
        self._event_is_polling.set()

    def run(self):
        udp_connection = UDPConnection(udp_port=5005)
        self.start_polling()

        ptp = PollingTimeProfile()
        prev_event_polling = None

        while not self._event_quit_request.is_set():
            if prev_event_polling != self._event_is_polling.is_set():
                # event pooling changed
                prev_event_polling = self._event_is_polling.is_set()
                if prev_event_polling:
                    logging.warning("UDP start, pid {}, priority {}".format(
                            self.pid, get_priority(self.pid)))
                else:
                    logging.warning("UDP stop")

            if not self._event_is_polling.is_set():
                ptp.stop()
                self._event_is_polling.wait(timeout=0.1)
            else:
                data = udp_connection.poll()
                t = udp_connection.timer.time
                ptp.update(t)
                if data is not None:
                    d = UDPData(string=data, time=t)
                    self.receive_queue.put(d)
                    if self._event_ignore_tag is not None and \
                            not d.startswith(self._event_ignore_tag):
                        for ev in self._event_trigger:
                            # set all connected trigger
                            ev.set()
                try:
                    udp_connection.send(self.send_queue.get_nowait())
                except:
                    pass

                # has connection changed?
                if self.event_is_connected.is_set() != udp_connection.is_connected:
                    if udp_connection.is_connected:
                        self.event_is_connected.set()
                    else:
                        self.event_is_connected.clear()

                if not udp_connection.is_connected:
                    udp_connection.timer.wait(200)

        udp_connection.unconnect_peer()

        logging.warning("UDP quit, {}".format(ptp.get_profile_str()))
