
import argparse

from . import __author__, __version__, gui


def cli():

    parser = argparse.ArgumentParser(
        prog="forcedaq",
        description=f"Command-line interface for pyforceDAQ {__version__}",
        epilog=f"Author: {__author__}",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument("SETTINGS_FILE", nargs="?", default="", help="settings file")

    parser.add_argument(
        "-l", "--launcher",
        action="store_true",
        default=False,
        help="Run with launcher GUI to edit settings and start recording",
    )

    args = parser.parse_args()

    if args.launcher:
        if len(args.SETTINGS_FILE) > 0:
            print("Can't use launcher and settings file")
            exit()

        from .gui import launcher
        return launcher.run()
    else:
        gui.run_settings(args.SETTINGS_FILE)



if __name__ == "__main__": # required because of threading
    cli()
