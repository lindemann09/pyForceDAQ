__version__ = "0.8.11c"
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

import sys as _sys
PYTHON3 = (_sys.version_info[0] == 3)
USE_DUMMY_SENSOR = False
