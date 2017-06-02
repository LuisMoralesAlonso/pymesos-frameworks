from __future__ import print_function

import sys
import time

def minimalTask(message):
    logging.debug(message)
    time.sleep(30)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 2:
        print("Usage: {} <message>".format(sys.argv[0]))
        sys.exit(1)
    else:
        minimalTask(sys.argv[1])
