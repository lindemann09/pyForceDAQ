# test client udo connection
from expyriment import control, stimuli, io, misc
from expyriment.misc import Clock

from forceDAQ.base.udp_connection import UDPConnection

# t : test connect
# q : quit client
# space : enter

control.set_develop_mode(True)
control.defaults.audiosystem_autostart=False
exp = control.initialize()

udp_connection = UDPConnection()
print(udp_connection)

if not udp_connection.connect_peer("192.168.178.5"):  # 41.89.98.24
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

