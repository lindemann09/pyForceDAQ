__author__ = 'Oliver Lindemann'


if __name__ == "__main__": # required because of threading
    from forceDAQ.gui import config, run

    config.plot_axis = False
    config.data_min_max = [-5, 30]

    run(
          device_name_prefix="Dev",
          device_ids = 1,
          sensor_names = ("FT30436"),
          calibration_folder="calibration",

          reverse_scaling = {1: ["Fz"]}, # key: device_id, parameter. E.g.:if x & z dimension of sensor 1 and z dimension of sensor 2 has to be flipped use {1: ["Fx", "Fz"], 2: ["Fz"]}
          remote_control=False,
          ask_filename= True,

          write_Fx=True,
          write_Fy=True,
          write_Fz=True,
          write_Tx=False,
          write_Ty=False,
          write_Tz=False,
          write_trigger1=True,
          write_trigger2=False,

          zip_data=False)
