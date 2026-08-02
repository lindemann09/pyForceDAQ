
import logging
from pathlib import Path

import appdirs


def set_logging(log_file):
    log_dir = Path(appdirs.AppDirs("").user_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file
    logging.basicConfig(filename=log_file,
                        encoding='utf-8',
                        format="[%(asctime)s] %(levelname)s: %(message)s",
                        datefmt="%m%d %H:%M:%S",
                        level=logging.INFO)
    return log_file