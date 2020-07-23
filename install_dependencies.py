try:
    import numpy
    #import pandas
    import expyriment
    import PySimpleGUI
    import PyDAQmx
    print("\nRequired packages are installed!")

except:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', "--upgrade", 'pip'])  # upgrade pkg
    subprocess.check_call([sys.executable, '-m', 'pip', 'install',
        "numpy", "expyriment", "PySimpleGUI", "PyDAQmx"])