__author__ = 'Oliver Lindemann'

if __name__ == "__main__": # required because of threding
    from forceDAQ import gui

    gui.start(device_ids= (1),
          calibration_files=("calibration/FT_demo.cal"),

          remote_control=False,
          ask_filename= False,

          write_deviceid=False,
          write_Fx=True,
          write_Fy=True,
          write_Fz=True,
          write_Tx=False,
          write_Ty=False,
          write_Tz=False,
          write_trigger1=True,
          write_trigger2=False,

          zip_data=True)
