__version__ = "0.8.9"
__author__ = "Oliver Lindemann"

"""
launch the GUI recorder from your Python program:
``
    from forceDAQ import gui

    gui.run_with_options(remote_control=False,
              ask_filename=True,
               calibration_file="FT_sensor1.cal")
``


import relevant stuff to program your own recorder:
``
    from forceDAQ import recorder
``

import relevant stuff for remote control of the GUI recorder:
``
    from forceDAQ import remote_control
``

For function to support data handling see the folder pyForceDAQ/analysis

"""

import sys as _sys
PYTHON3 = (_sys.version_info[0] == 3)
USE_DUMMY_SENSOR = False
