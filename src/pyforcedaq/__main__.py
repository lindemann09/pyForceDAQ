import argparse

from . import __author__, __version__, constants


def print_version():
    print("+" + "-" * 23 + "+")
    print(f"| pyforceDAQ {__version__}".ljust(24) + "|")
    print("+" + "-" * 23 + "+")

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

    parser.add_argument(
        "--dll",
        action="store_true",
        default=False,
        help="Use self compiled ATI DLL",
    )

    args = parser.parse_args()
    if args.mock:
        constants.DAQ_TYPE = constants.MOCK_SENSOR
    else:
        constants.DAQ_TYPE = constants.NIDAQMX # use NI-DAQmx
    constants.USE_AIFTT = not args.dll

    print_version()
    if not args.omit_launcher:
        if len(args.SETTINGS_FILE) > 0:
            print("Can't use launcher and settings file")
            exit()

        from .launcher import run_launcher

        return run_launcher()
    else:
        from .gui import run_settings_file

        if len(args.SETTINGS_FILE) == 0:
            print("No settings file provided, can't start recording")
            exit()

        run_settings_file(args.SETTINGS_FILE)


if __name__ == "__main__":  # required because of threading
    cli()
