import logging
import time

from core.extractors import Extractor

logger = logging.getLogger("Time")


class _Time:
    """ Time object for syncing local time with server time """

    def __init__(self):
        self.server_offsets = []

    def sync(self, response):
        """ Syncs the local time with the server time """

        server_time = Extractor.get_server_time(response)
        if server_time:
            current_time = time.strftime("%H:%M:%S", time.localtime())  # Everyone plays in their own timezone
            current_seconds = self.convert_to_seconds(current_time)
            server_seconds = self.convert_to_seconds(server_time)
            self.server_offsets.append(server_seconds - current_seconds)

            if len(self.server_offsets) > 5:
                self.server_offsets.pop(0)

            logger.debug("Our time: %s, server time: %s, offset: %d", current_time, server_time,
                         self.server_offsets[-1])

    @staticmethod
    def convert_to_seconds(time_str):
        """ Converts a time string(00:00:00) to seconds """

        parts = time_str.split(":")
        if len(parts) != 3:
            logger.error("Invalid time string: %s", time_str)
            return 0

        return sum(int(x) * 60 ** i for i, x in enumerate(reversed(time_str.split(":"))))

    def get_avg_offset(self):
        """ Returns the average offset of the server time """

        if len(self.server_offsets) == 0:
            return 0
        return sum(self.server_offsets) / len(self.server_offsets)

    def get_time(self):
        """ Returns the server time """

        current_seconds = int(time.time())
        server_time = current_seconds + self.get_avg_offset()
        logger.debug("Our time: %d, calculated server time: %d", current_seconds, server_time)
        return server_time


Time = _Time()
