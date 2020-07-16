__version__ = "0.8.2"
__author__ = "Oliver Lindemann"

"""
to use the GUI recorder:
``
    from forceDAQ import gui

    gui.start(remote_control=False,
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

#TODO setting files

import sys as _sys
PYTHON3 = (_sys.version_info[0] == 3)


