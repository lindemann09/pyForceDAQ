"""
Functions to read your force and event data
"""

__author__ = 'Oliver Lindemann'

import gzip
import pandas as pd

TAG_COMMENTS = "#"
TAG_UDPDATA  = TAG_COMMENTS + "UDP"
TAG_SOFTTRIGGER = TAG_COMMENTS +"T"

def read_force_data(path):
    """returns force data pandas table"""
    if path.endswith(".gz"):
        comp = "gzip"
    else:
        comp = None
    return pd.read_csv(path, comment=TAG_COMMENTS, compression=comp)

def read_event_data(path):
    """reading trigger and udp data
    Returns: event data as pandas data frame

    """

    trigger = []
    udp = []
    if path.endswith("gz"):
        fl = gzip.open(path, "r")
    else:
        fl = open(path, "r")

    first_comment_line = True
    for ln in fl:
        if ln.startswith(TAG_COMMENTS):
            if first_comment_line:
                # print ln.strip()
                first_comment_line = False
            elif ln.startswith(TAG_UDPDATA):
                udp.append(ln[len(TAG_UDPDATA)+1:].strip().split(","))
            elif ln.startswith(TAG_SOFTTRIGGER):
                trigger.append(ln[len(TAG_SOFTTRIGGER)+1:].strip().split(","))
    fl.close()

    trigger = pd.DataFrame(trigger, columns=["time", "value"])
    trigger["type"] = "softtrigger"
    udp = pd.DataFrame(udp, columns=["time", "value"])
    udp["type"] = "udp"

    return trigger.append(udp)
