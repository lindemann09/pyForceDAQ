![pyForceDAQ](https://github.com/lindemann09/pyForceDAQ/blob/master/src/pyforcedaq/gui/forceDAQ_logo.png)

Python DAQ library and application for ATI force sensors and NI-DAQ

*Released under the MIT License*

 Oliver Lindemann <lindemann@cognitive-psychology.eu>


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
