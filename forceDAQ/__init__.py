__version__ = "0.9.2"
__author__ = "Oliver Lindemann"

"""
launch the GUI force from your Python program:
``
    from forceDAQ import gui

    gui.run_with_options(remote_control=False,
              ask_filename=True,
               calibration_file="FT_sensor1.cal")
``


import relevant stuff to program your own force:
``
    from forceDAQ import force
``

import relevant stuff for remote control of the GUI force:
``
    from forceDAQ import remote_control
``

For function to support data handling see the folder pyForceDAQ/analysis

"""

USE_DUMMY_SENSOR = False

import sys as _sys
if _sys.version_info[0] != 3 or _sys.version_info[1]<5:
    raise RuntimeError("pyForceDAQ {0} ".format(__version__) +
                      "is not compatible with Python {0}.{1}. ".format(
                                                    _sys.version_info[0],
                                                    _sys.version_info[1]) +
                       "Please use Python 3.5+.")
