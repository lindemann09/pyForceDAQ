import sys
import subprocess

while True:
    x = subprocess.Popen([sys.executable, "forceDAQ_GUI.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    x.wait()
    a = raw_input("quit recording (y/n)? ")
    if a in ["j", "J", "y", "Y", "q", "Q"]:
        break
