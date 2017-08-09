import asyncio
import logging
import os

class Tg2Sock(object):

    def __init__(self, args):
        self._args = args
        self._logger = logging.getLogger('tg2sock')

    def run(self):
        pass

    async def start(self):
        self._logger.debug("starting server on %s", self._args.control)
        if os.path.exists(self._args.control):
            os.unlink(self._args.control)
        await asyncio.start_unix_server(self.accept_client, path=self._args.control)

    def accept_client(self, reader, writer):
        pass
