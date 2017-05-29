from __future__ import print_function

import sys
import time
from addict import Dict

def minimalTask(message):
    logging.debug(message)
    time.sleep(30)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    minimalTask(sys.argv[1])
