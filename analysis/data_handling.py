"""
import this module to have all relevant functions to read your force data output
"""

__author__ = 'Oliver Lindemann'

import gzip
import pandas as pd

TAG_COMMENTS = "#"
TAG_UDPDATA  = TAG_COMMENTS + "UDP"
TAG_SOFTTRIGGER = TAG_COMMENTS +"T"

def read_force_data(path):
    """returns force data pandas table"""
    return pd.read_csv(path, comment=TAG_COMMENTS)

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

    trigger =  pd.DataFrame(trigger, columns=["time", "value"])
    trigger["type"] = "softtrigger"
    udp = pd.DataFrame(udp, columns=["time", "value"])
    udp["type"] = "udp"

    return trigger.append(udp)


def force_data_csv2hdf5(path, complevel=9):
    """converting csv force data to hdf5 file
    with three seperate tables:
        * force
        * events
    """

    print "converting to hdf5", path

    hdf_filename = path[:path.find(".")] + ".hdf5"
    hdf = pd.HDFStore(hdf_filename, mode = "w", complib='zlib',
                            complevel=complevel)

    hdf['force'] = read_force_data(path)
    hdf['events']  = read_event_data(path)
    hdf.close()

def extract_event_data(path):
    """extracting non force data and saving *.trigger.csv and *.udp.csv"""

    print "extracting event data", path
    events = read_event_data(path)
    i = path.find(".")
    if path.endswith(".gz"):
        fl = gzip.open(path[:i] + ".events.csv.gz", "w")
    else:
        fl = open(path[:i] + ".events.csv", "w")
    events.to_csv(fl, index=False)
    fl.close()
