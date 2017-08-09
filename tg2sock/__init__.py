import asyncio
import logging
import os
import telepot.aio
import telepot.aio.loop


class Tg2Sock(object):

    def __init__(self, args):
        self._args = args
        self._logger = logging.getLogger('tg2sock')
        with open(self._args.token_file) as token_file:
            self._bot = telepot.aio.Bot(token_file.readline())

    def handle(self, msg):
        pass

    async def run_forever(self):
        self._logger.debug("starting server on %s", self._args.control)
        if os.path.exists(self._args.control):
            os.unlink(self._args.control)
        await asyncio.start_unix_server(self.accept_client, path=self._args.control)
        await telepot.aio.loop.MessageLoop(self.handle, self._bot).run_forever()

    def accept_client(self, reader, writer):
        pass
