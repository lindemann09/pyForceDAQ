__author__ = 'Oliver Lindemann'


if __name__ == "__main__": # required because of threding
    from forceDAQ.gui import start, config

    config.plot_axis = False

    start(
          device_ids = (1, 2),
          sensor_names = ("FT9093", "FT17809"),
          calibration_folder="calibration",
          device_name_prefix="Dev",

          reverse_scaling = {1: ["Fz", "Fx"]}, # key: device_id, parameter
          remote_control=False,
          ask_filename= False,

          write_Fx=True,
          write_Fy=True,
          write_Fz=True,
          write_Tx=False,
          write_Ty=False,
          write_Tz=False,
          write_trigger1=True,
          write_trigger2=False,

          zip_data=False)
