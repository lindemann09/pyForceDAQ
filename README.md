![pyForceDAQ](https://github.com/lindemann09/pyForceDAQ/blob/master/src/pyforcedaq/gui/forceDAQ_logo.png)

Python DAQ library and application for ATI force sensors and NI-DAQ

**LSL Version**

*Released under the MIT License*

 Oliver Lindemann <lindemann@cognitive-psychology.eu>

Dependencies
------------

* Python 3.0
* [NumPy](http://www.numpy.org/) 1.7 or higher
* [PyDAQmx](https://pythonhosted.org/PyDAQmx/installation.html)
* The GUI application (`forceDAQ.gui`) depends furthermore on [Expyriment](http://docs.expyriment.org/Installation.html) 0.8.0 or higher

Stringly recommended for GUI interface:
* [PySimpleGUI](https://pysimplegui.readthedocs.io/)

Installation
------------

* Create the shared library `atidaq.dll` (or `atidaq.so` for Linux) using
 `Makefile` in the folder `atidaq_cdll`. A complied version of `atidaq.dll
 ` can be also found in the `dll` subfolder
* Make the library available by coping it in your system folder

To install pyForceDAQ from release-zipfile

1. Ensure that [Python 3](https://www.python.org/) is installed
2. Download and unpack zipfile file
3. run `install_dependencies.py`
4. run `forceDAQ_GUI.py`
5. edit settings via GUI if required

**Note:** The software uses a mock sensor and simulates
data, if no device is connected. It enforce mock sensor set (before importing further packages modules):

``pyforcedaq.USE_MOCK_SENSOR = True``

Development
-----------

https://github.com/lindemann09/pyForceDAQ

Please [submit](https://github.com/lindemann09/pyForceDAQ/issues/new)
any bug you encounter to the Github issue tracker.
