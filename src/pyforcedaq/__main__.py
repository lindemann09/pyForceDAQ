import argparse
import logging

from . import APPNAME, LOGFILE, __author__, __version__, constants
from .lib.settings import AppSettings


def print_info(logfilename:str|None = None):
    print("+" + "-" * 23 + "+")
    print(f"| {APPNAME} {__version__}".ljust(24) + "|")
    print("+" + "-" * 23 + "+")
    if logfilename is not None:
        print(f"Logging to {logfilename}")


def cli():
    logging.info("==== App started ====")
    parser = argparse.ArgumentParser(
        prog="forcedaq",
        description=f"Command-line interface for {APPNAME} {__version__}",
        epilog=f"Author: {__author__}",
    )

    parser.add_argument("SETTINGS_FILE", nargs="?", default="", help="settings file")

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--logfile",
        action="store_true",
        default=False,
        help="show logfile path",
    )

    parser.add_argument(
        "-o",
        "--omit-launcher",
        action="store_true",
        default=False,
        help="Omit launcher GUI and start recording directly",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Use mock sensor",
    )


    args = parser.parse_args()

    if args.logfile:
        print(f"Log file: {LOGFILE}")
        return

    if args.mock:
        constants.DAQ_TYPE = constants.DaqType.MOCK_SENSOR
    else:
        constants.DAQ_TYPE = constants.DaqType.NIDAQMX # use NI-DAQmx

    print_info(str(LOGFILE))
    if not args.omit_launcher:
        if len(args.SETTINGS_FILE) > 0:
            print("Can't use launcher and settings file")
            exit()

        from .launcher import run_launcher
        try:
            return run_launcher()
        except FileNotFoundError:
            ans = input("No settings file found. Create one with defaults? [Y/n]: ")
            if ans.lower() == "y" or ans.lower() == "yes":
                AppSettings(constants.DEFAULT_SETTINGS_FILE, create_if_not_exists=True)  # create new settings file with defaults
            else:
                exit()

    else:
        from .gui import run_settings_file

        if len(args.SETTINGS_FILE) == 0:
            print("No settings file provided, can't start recording")
            exit()

        run_settings_file(args.SETTINGS_FILE)


if __name__ == "__main__":  # required because of threading
    cli()
