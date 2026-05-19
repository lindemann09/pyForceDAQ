from . import __author__, __version__, gui

if __name__ == "__main__": # required because of threading
    gui.run_with_launcher() # gui.run(), gui.run_with_options()
