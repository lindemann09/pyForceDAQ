__author__ = 'Oliver Lindemann'
import forceDAQ
forceDAQ.USE_DUMMY_SENSOR = True
TRY_TK_LAUNCHER = True

if __name__ == "__main__": # required because of threading
    from forceDAQ.gui import run

    tk_launcher = None
    if TRY_TK_LAUNCHER:
        try:
            from forceDAQ.gui import tk_launcher
        except:
            print("Warning: Install PySimpleGUI to use tk_launcher GUI.")

    if tk_launcher is not None:
        tk_launcher.run()
    else:
        run()