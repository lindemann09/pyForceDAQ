"""DAQ tool to record response force data

Oliver Lindemann, 2026


launch the GUI force from your Python program:
``
    from pyforcedaq import gui

    gui.run(ask_filename=True,
               calibration_file="FT_sensor1.cal") TODO
``


import relevant stuff to program your own force:
``
    from pyforcedaq import lib as forcedaqlib
``


For function to support data handling see the folder pyForceDAQ/analysis

Oliver Lindemann
"""

import sys as _sys
from importlib.metadata import version

from .tools import _log

APPNAME = "pyForceDAQ"
__version__ = version(APPNAME)
__author__ = "Oliver Lindemann"


if _sys.version_info[0] != 3 or _sys.version_info[1] < 12 or _sys.version_info[1] > 13:
    raise RuntimeError(
        f"{APPNAME} {__version__} "
        + f"is not compatible with Python {_sys.version_info[0]}.{_sys.version_info[1]}. "
        + "Please use Python 3.12 or 3.13."
    )
LOGFILE = _log.set_logging(log_file=f"{APPNAME}.log")
