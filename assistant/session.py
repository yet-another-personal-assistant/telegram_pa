import asyncio
import os

class Session(object):

    _server = None

    def __init__(self, bot, chat_id, path, state_machine):
        self._bot = bot
        self._chat_id = chat_id
        self._sm = state_machine
        self._path = path

    def start(self):
        self._sm.handle_event('start')

    async def start_server(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
        self._server = await asyncio.start_unix_server(self.accept_client, path=self._path)

    async def send_message(self, message):
        await self._bot.sendMessage(self._chat_id, message)

    async def handle_remote(self, message):
        self._sm.handle_event('message', message)

    def stop(self):
        self._server.close()
        os.unlink(self._path)

    def accept_client(self, reader, writer):
        task = asyncio.Task()
        def client_gone(task):
            writer.close()
        task.add_done_callback(client_gone)
