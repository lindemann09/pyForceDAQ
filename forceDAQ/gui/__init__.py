__author__ = "Oliver Lindemann"

from ._run import run, run_with_options
from ._settings import settings


def run_with_launcher():
    from . import launcher  # might cause an error
    launcher.run()
