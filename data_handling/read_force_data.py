"""
Functions to read your force and event data
"""

__author__ = 'Oliver Lindemann'

import os
import sys
import gzip
from copy import copy
from collections import OrderedDict
import numpy as np


TAG_COMMENTS = "#"
TAG_UDPDATA  = TAG_COMMENTS + "UDP"
TAG_SOFTTRIGGER = TAG_COMMENTS +"T"


def _csv(line):
    return list(map(lambda x: x.strip(), line.split(",")))

def DataFrameDict(data, varnames):
    """data frame: Dict of numpy arrays

    does not require Pandas, but can be easily converted to pandas dataframe
    via pandas.DataFrame(data_frame_dict)

    """

    rtn = OrderedDict()
    for v in varnames:
        rtn[v] = []

    for row in data:
        for v, d in zip(varnames, row):
            rtn[v].append(d)

    return rtn


def data_frame_to_text(data_frame):
    rtn = ",".join(data_frame.keys())
    rtn += "\n"
    for x in np.array(list(data_frame.values())).T:
        rtn += ",".join(x) + "\n"
    return rtn


def read_raw_data(path):
    """reading trigger and udp data

    Returns: data, udp_event, soft_trigger and comments

            data, udp_event, soft_trigger: DataFrameDict
            comments: text string
    """



    trigger = []
    udp_events = []
    comments = ""
    data = []
    varnames = None
    app_dir = os.path.split(sys.argv[0])[0]
    path = os.path.abspath(os.path.join(app_dir, path))

    if path.endswith("gz"):
        fl = gzip.open(path, "r")
    else:
        fl = open(path, "r")

    for ln in fl:
        if ln.startswith(TAG_COMMENTS):
            comments += ln
            if ln.startswith(TAG_UDPDATA + ","):
                udp_events.append(_csv(ln[len(TAG_UDPDATA) + 1:]))
            elif ln.startswith(TAG_SOFTTRIGGER):
                trigger.append(_csv(ln[len(TAG_SOFTTRIGGER) + 1:]))
        else:
            # data
            if varnames is None:
                # first row contains varnames
                varnames = _csv(ln)
            else:
                data.append(_csv(ln))
    fl.close()

    return (DataFrameDict(data, varnames),
            DataFrameDict(udp_events, ["time", "value"]),
            DataFrameDict(trigger, ["time", "value"]),
            comments)


def convert_raw_data(filepath):
    """preprocessing raw pyForceData:

    """

    filepath = os.path.join(os.path.split(sys.argv[0])[0], filepath)
    print("converting {}".format(filepath))

    if filepath.endswith(".gz"):
        new_filename = filepath[:-7]
    else:
        new_filename = filepath[:-4]
    new_filename += ".conv.csv.gz"

    data, udp_event, trigger, comments = read_raw_data(filepath)
    print("{} samples".format(len(data["time"])))

    # adapt timestamps
    new_data = copy(data)
    delay = new_data.pop("delay")
    time = new_data["time"]
    newtime = range(0, len(time))
    new_data["time"] = newtime



    with gzip.open(new_filename, "wt") as fl:
        fl.write(comments.strip() + "\n")
        fl.write(data_frame_to_text(new_data))
