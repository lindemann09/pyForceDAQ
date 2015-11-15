"""
import this module to have all relevant classes and functions to analyse your force data
"""

__author__ = 'Oliver Lindemann'

import gzip
import pandas as pd

from base.forceDAQ_types import TAG_SOFTTRIGGER, TAG_UDPDATA, TAG_COMMENTS


def read_force_data(path):
    """returns force data pandas table"""
    return pd.read_csv(path, comment=TAG_COMMENTS)

def read_non_force_data(path):
    """reading trigger and udp data
    Returns
        trigger: pandas data frame
        udp: pandas data frame

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

    return  pd.DataFrame(trigger, columns=["time", "value"]), \
            pd.DataFrame(udp, columns=["time", "value"])

def force_data_csv2hdf5(path, complevel=9):
    """converting csv force data to hdf5 file
    with three seperate tables:
        * force
        * trigger
        * udp
    """

    print "converting to hdf5", path

    f = read_force_data(path)
    t, u = read_non_force_data(path)

    hdf_filename = path[:path.find(".")] + ".hdf5"
    hdf = pd.HDFStore(hdf_filename, mode = "w", complib='zlib',
                            complevel=complevel)
    hdf['force'], hdf['trigger'], hdf['udp'] = f, t, u
    hdf.close()

def extract_non_force_data(path):
    """extracting non force data and saving *.trigger.csv and *.udp.csv"""

    print "extracting non force data", path

    t, u = read_non_force_data(path)
    i = path.find(".")
    if path.endswith(".gz"):
        trigger_file = gzip.open(path[:i] + ".trigger.csv.gz", "w")
        udp_file = gzip.open(path[:i] + ".udp.csv.gz", "w")
    else:
        trigger_file = open(path[:i] + ".trigger.csv", "w")
        udp_file = open(path[:i] + ".udp.csv", "w")

    t.to_csv(trigger_file)
    u.to_csv(udp_file)

    trigger_file.close()
    udp_file.close()
