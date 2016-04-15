#!/usr/bin/env python

"""
Functions to convert force data

This module can be also executed.
"""

__author__ = 'Oliver Lindemann'

import gzip
import pandas as pd
from .read_force_data import read_force_data, read_event_data

def force_data_csv2hdf5(path, complevel=9):
    """converting csv force data to hdf5 file
    with three seperate tables:
        * force
        * events
    """

    print("converting to hdf5", path)

    hdf_filename = path[:path.find(".")] + ".hdf5"
    hdf = pd.HDFStore(hdf_filename, mode = "w", complib='zlib',
                            complevel=complevel)

    hdf['force'] = read_force_data(path)
    hdf['events']  = read_event_data(path)
    hdf.close()

def extract_event_data(path):
    """extracting non force data and saving *.trigger.csv and *.udp.csv"""

    print("extracting event data", path)
    events = read_event_data(path)
    i = path.find(".")
    if path.endswith(".gz"):
        fl = gzip.open(path[:i] + ".events.csv.gz", "w")
    else:
        fl = open(path[:i] + ".events.csv", "w")
    events.to_csv(fl, index=False)
    fl.close()

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(usage="convert_data.py [OPTIONS] [FILENAME]\n" +
                                "Please specify an option and the file to be preprocessed")
    parser.add_option("-e", "--extract", dest="extract", action="store_true",
                  help="extract event data", default=False)
    parser.add_option("-f", "--hdf5", dest="hdf5", action="store_true",
                  help="converte to hdf5", default=False)
    (options, args) = parser.parse_args()

    if len(args)==0:
        parser.print_help()
        exit(1)
    elif options.extract:
        extract_event_data(args[0])
    elif options.hdf5:
        force_data_csv2hdf5(args[0])
    else:
        parser.print_help()
        exit(1)
