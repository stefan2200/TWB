import signal
import sys


def signal_handler(sig, frame):
    print("Exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
