"""DAQ tool to record response force data

Oliver Lindemann, 2026


launch the GUI force from your Python program:
``
    from pyforcedaq import gui

    gui.run(ask_filename=True,
               calibration_file="FT_sensor1.cal")
``


import relevant stuff to program your own force:
``
    from pyforcedaq import force
``


For function to support data handling see the folder pyForceDAQ/analysis

Oliver Lindemann
"""

from importlib.metadata import version

__version__ = version("pyforcedaq")
__author__ = "Oliver Lindemann"

import sys as _sys

USE_MOCK_SENSOR = False # <-- change for usage in lab to False

if _sys.version_info[0] != 3 or _sys.version_info[1]<12:
    raise RuntimeError("pyForceDAQ {0} ".format(__version__) +
                      "is not compatible with Python {0}.{1}. ".format(
                                                    _sys.version_info[0],
                                                    _sys.version_info[1]) +
                       "Please use Python 3.12+.")
