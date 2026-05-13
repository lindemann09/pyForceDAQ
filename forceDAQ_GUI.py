__author__ = 'Oliver Lindemann'

import forceDAQ
forceDAQ.USE_DUMMY_SENSOR = False # <-- change for usage in lab to False

if __name__ == "__main__": # required because of threading
    from forceDAQ.gui import run
    #tk_launcher = None # use no launcher
    
    try:
        from forceDAQ.gui import tk_launcher
    except:
        tk_launcher = None
        print("Warning: Install PySimpleGUI to use tk_launcher GUI.")

    if tk_launcher is not None:
        tk_launcher.run()
    else:
        run()
