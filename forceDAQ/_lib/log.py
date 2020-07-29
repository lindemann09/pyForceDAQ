import os
import sys
import logging

def set_logging(data_directory, log_file= "recording.log"):
    base_dir = os.path.split(sys.argv[0])[0]
    log_dir = os.path.join(base_dir, data_directory)
    try:
        os.mkdir(log_dir)
    except:
        pass
    log_file = os.path.abspath(os.path.join(log_dir, log_file))
    logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename=log_file,
                    filemode='a')
    return log_file
