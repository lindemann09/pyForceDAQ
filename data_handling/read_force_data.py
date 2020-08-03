"""
Functions to read your force and event data
"""

__author__ = 'Oliver Lindemann'

import os
import sys
import gzip
from collections import OrderedDict
import numpy as np

TAG_COMMENTS = "#"
TAG_UDPDATA  = TAG_COMMENTS + "UDP"
TAG_DAQEVENTS = TAG_COMMENTS + "T"

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

    Returns: data, udp_event, daq_events and comments

            data, udp_event, daq_events: DataFrameDict
            comments: text string
    """

    daq_events = []
    udp_events = []
    comments = ""
    data = []
    varnames = None
    app_dir = os.path.split(sys.argv[0])[0]
    path = os.path.abspath(os.path.join(app_dir, path))

    if path.endswith("gz"):
        fl = gzip.open(path, "rt")
    else:
        fl = open(path, "rt")

    for ln in fl:
        if ln.startswith(TAG_COMMENTS):
            comments += ln
            if ln.startswith(TAG_UDPDATA + ","):
                udp_events.append(_csv(ln[len(TAG_UDPDATA) + 1:]))
            elif ln.startswith(TAG_DAQEVENTS):
                daq_events.append(_csv(ln[len(TAG_DAQEVENTS) + 1:]))
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
            DataFrameDict(daq_events, ["time", "value"]),
            comments)
