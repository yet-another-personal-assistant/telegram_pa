import asyncio
import logging
import os
import telepot
import telepot.aio.loop


class Tg2Sock(object):

    def __init__(self, args):
        self._args = args
        self._logger = logging.getLogger('tg2sock')
        with open(self._args.token_file) as token_file:
            for line in token_file:
                key, value = line.split()
                if key == "TOKEN":
                    self._bot = telepot.aio.Bot(value)

    async def run_forever(self):
        self._logger.debug("starting server on %s", self._args.control)
        if os.path.exists(self._args.control):
            os.unlink(self._args.control)
        await asyncio.start_unix_server(self.accept_client, path=self._args.control)
        await telepot.aio.loop.MessageLoop(self._bot, self.handle).run_forever()

    def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        print("chat_id: {}, message: {}".format(chat_id, msg.get('text', "(none)")))

    def accept_client(self, reader, writer):
        pass
