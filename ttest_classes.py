from forceDAQ.gui import plotter
from forceDAQ.gui.layout import colours

import expyriment
expyriment.control.set_develop_mode(True)
expyriment.control.defaults.audiosystem_autostart=False
expyriment.control.initialize()

pl = plotter.Plotter(n_data_rows=3, data_row_colours=colours[:3])
pl.clear_area()
print(pl.size)
print(pl.width)
#time.sleep(3)