__author__ = 'Oliver Lindemann'

import forceDAQ
forceDAQ.USE_DUMMY_SENSOR = True # <-- change for usage in lab to False

if __name__ == "__main__": # required because of threading
    from forceDAQ.gui import run

    tk_launcher = None
    try:
        from forceDAQ.gui import tk_launcher
    except:
        print("Warning: Install PySimpleGUI to use tk_launcher GUI.")

    if tk_launcher is not None:
        tk_launcher.run()
    else:
        run()
