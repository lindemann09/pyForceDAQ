level_detection_parameter = "Fz"
window_font = "freemono"
moving_average_size = 5
screen_refresh_interval_indicator = 300
gui_screen_refresh_interval_plotter = 50
data_min_max=[-5, 30]
plotter_pixel_min_max=[-250, 250]
indicator_pixel_min_max=[-150, 150]
plot_axis = True

plot_data_indicator_for_single_sensor = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]  # sensor, parameter
plot_data_plotter_for_single_sensor = [ (0,0), (0,1), (0,2) ] # plotter can't plot torques # FIXME

plot_data_indicator_for_two_sensors = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]  # sensor, parameter
plot_data_plotter_for_two_sensors = [ (0,2), (1,2) ] # plotter can't plot torques