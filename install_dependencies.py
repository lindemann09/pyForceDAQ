import sys
if sys.version_info[0] != 3 or sys.version_info[1]<5:
    raise RuntimeError("pyForceDAQ is not compatible with Python {0}.{1}.".format(
                                                    sys.version_info[0],
                                                    sys.version_info[1]) +
                       " Please use Python 3.5+.")

try:
    import numpy
    #import pandas
    import expyriment
    import PySimpleGUI
    import PyDAQmx
    import psutil
    print("\nRequired packages are installed!")

except:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', "--upgrade", 'pip'])  # upgrade pkg
    subprocess.check_call([sys.executable, '-m', 'pip', 'install',
        "numpy", "expyriment", "PySimpleGUI", "PyDAQmx", "psutil"])
