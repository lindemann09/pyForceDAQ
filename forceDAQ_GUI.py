__author__ = 'Oliver Lindemann'

if __name__ == "__main__": # required because of threading
    from forceDAQ.gui import run_settings_file, settings

    settings.save()
    run_settings_file()