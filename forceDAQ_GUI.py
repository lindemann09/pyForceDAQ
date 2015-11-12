__author__ = 'Oliver Lindemann'

if __name__=="__main__":
    from forceDAQ import gui
    remote_control = False
    gui.start(remote_control=remote_control,
                  ask_filename=not remote_control,
                  calibration_file="FT_demo.cal")
