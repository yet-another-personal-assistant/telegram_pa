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
                elif key == "OWNER":
                    self._owner_id = int(value)
        self._writer = None

    async def run_forever(self):
        self._logger.debug("starting server on %s", self._args.control)
        if os.path.exists(self._args.control):
            os.unlink(self._args.control)
        await asyncio.start_unix_server(self.accept_client, path=self._args.control)
        await telepot.aio.loop.MessageLoop(self._bot, self.handle).run_forever()

    def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        self._writer.write("chat_id:{},message:{}\n"
                           .format(chat_id, msg.get('text', "(none)"))
                           .encode())

    def accept_client(self, reader, writer):
        self._writer = writer
        asyncio.Task(self.handle_client(reader, writer))

    async def handle_client(self, reader, writer):
        while True:
            sdata = await reader.readline()
            if not sdata:
                break
            await self._bot.sendMessage(self._owner_id, sdata.decode())
        writer.close()
