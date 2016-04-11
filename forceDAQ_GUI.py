__author__ = 'Oliver Lindemann'

from forceDAQ import gui

gui.start(device_ids= (1),
          calibration_file=("calibration/FT_demo.cal"),

          remote_control=True,
          ask_filename= True,

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
