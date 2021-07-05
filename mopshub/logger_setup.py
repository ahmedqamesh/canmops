import logging
import sys
from coloredlogs import ColoredFormatter

_logger = logging.getLogger('mopshub_log')
_logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('mopshub_log', 'w')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

ch = logging.StreamHandler()
ch.setStream(sys.stdout)
ch.setLevel(logging.WARNING)

_logger.addHandler(fh)
_logger.addHandler(ch)

