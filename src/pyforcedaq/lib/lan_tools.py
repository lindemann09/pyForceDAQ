import os
import socket
from subprocess import check_output


def get_lan_ip():
    if os.name == "nt":
        # Windows
        return socket.gethostbyname(socket.gethostname())
    else:
        # Linux and macOS
        try:
            # Try Linux command first
            rtn = check_output(["hostname", "-I"]).decode().strip()
            return rtn.split()[0] if rtn else None
        except:
            try:
                # Fallback to macOS command
                rtn = check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
                return rtn if rtn else None
            except:
                # Fallback to socket method if both commands fail
                return socket.gethostbyname(socket.gethostname())

