# test client sever connection
from expyriment import control, stimuli, io, misc
from expyriment.misc import Clock

from forceDAQ import PYTHON3
from forceDAQ.base.udp_connection import UDPConnection, \
    UDPConnectionProcess

def client(server_ip):
    # t : test connect
    # q : quit client
    # space : enter

    control.set_develop_mode(True)
    control.defaults.audiosystem_autostart=False
    exp = control.initialize()

    udp_connection = UDPConnection()
    print(udp_connection)

    if not udp_connection.connect_peer(server_ip):
        print("error connecting to peer")
        exit()

    stimuli.TextScreen("connected to " + udp_connection.peer_ip,
                     "\nSPACE: send text\nT: trigger test\nQ: quit").present()

    c = Clock()

    while True:
        key = exp.keyboard.check()
        if key == ord("q"):
            break
        elif key == misc.constants.K_SPACE:
            text = io.TextInput().get()
            stimuli.BlankScreen().present()
            print("send: {} {}".format(c.time, text))
            udp_connection.send(text)
        elif key == ord("t"):
            times = []
            for cnt in range(20):
                stimuli.TextLine("ping test " + str(cnt)).present()
                c.reset_stopwatch()
                ok, time = udp_connection.ping(timeout=1)
                print("answer received in {} ms".format(c.stopwatch_time))
                times.append(time)
                c.wait(100)
            stimuli.BlankScreen().present()
            print(times)

        feedback = udp_connection.poll()
        if feedback is not None:
            print("received: {} {}".format(c.time, feedback))

    udp_connection.unconnect_peer()

def server():
    # process
    udp_p = UDPConnectionProcess()
    udp_p.start()
    udp_p.start_polling()

    connected = None
    while True:
        data = udp_p.receive_queue.get()
        if data is not None:
            # udp_p.send_queue.put(data.string)
            print("received: {}".format(data.string))

        if udp_p.event_is_connected.is_set() != connected:
            connected = udp_p.event_is_connected.is_set()
            if connected:
                print("Server is connected")
            else:
                print("Server is unconnected")
                break

    udp_p.stop()
    udp_p.join()

if __name__ == "__main__":

    if PYTHON3:
        x = input("Is this a Server (y/n)? ")
    else:
        x = raw_input("Is this a Server (y/n)? ")

    if x=="y" or x=="yes":
        server()
    else:
        client(server_ip="192.168.178.5")
