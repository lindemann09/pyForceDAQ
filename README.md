![pyForceDAQ](https://github.com/lindemann09/pyForceDAQ/blob/master/forceDAQ/gui/forceDAQ_logo.png)

Python DAQ library and application for ATI force sensors and NI-DAQ


*Released under the MIT License*

 Oliver Lindemann <oliver.lindemann@cognitive-psychology.eu>

Dependencies
------------

* Python 2.7 (<3.0)
* [NumPy](http://www.numpy.org/) 1.7 or higher
* [PyDAQmx](https://pythonhosted.org/PyDAQmx/installation.html)
* The GUI application (`forceDAQ.gui`) depends furthermore on [Expyriment](http://docs.expyriment.org/Installation.html) 0.8.0 or higher


Installation
------------

* Create the shared library `atidaq.dll` (or `atidaq.so` for Linux) using
 `Makefile` in the folder `atidaq_cdll`. A complied version of `atidaq.dll
 ` can be also found in the `dll` subfolder
* Make the library available by coping it in your system folder 

Development
-----------

https://github.com/lindemann09/pyForceDAQ

Please [submit](https://github.com/lindemann09/pyForceDAQ/issues/new) any bugs you encounter to the Github issue tracker.
