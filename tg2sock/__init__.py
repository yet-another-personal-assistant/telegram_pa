import asyncio
import logging
import os
import telepot
import telepot.aio.loop


def _tg2str(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    return "chat_id:{},message:{}\n".format(chat_id, msg.get('text'))


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
        self._writers = []
        self._stored = []

    async def run_forever(self):
        self._logger.debug("starting server on %s", self._args.control)
        if os.path.exists(self._args.control):
            os.unlink(self._args.control)
        await asyncio.start_unix_server(self.accept_client, path=self._args.control)
        await telepot.aio.loop.MessageLoop(self._bot, self.handle).run_forever()

    def handle(self, msg):
        asyncio.Task(self.handle_remote_message(msg))

    def accept_client(self, reader, writer):
        asyncio.Task(self.handle_client(reader, writer))

    def _register_backend(self, writer):
        self._writers.append(writer)
        while self._stored:
            writer.write(self._stored.pop(0))

    async def handle_client(self, reader, writer):
        while True:
            sdata = await reader.readline()
            if not sdata:
                break
            await self.handle_local_message(sdata.decode(), reader, writer)
        if writer in self._writers:
            self._writers.remove(writer)
        writer.close()

    async def handle_local_message(self, message, reader, writer):
        message = message.strip()
        if message == 'register backend':
            self._register_backend(writer)
            return
        elif message:
            await self._bot.sendMessage(self._owner_id, message)

    async def handle_remote_message(self, message):
        line = _tg2str(message).encode()
        if self._writers:
            self._writers[-1].write(line)
        else:
            self._stored.append(line)
