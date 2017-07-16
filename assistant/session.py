import asyncio
import os

class Session(object):

    def __init__(self, bot, chat_id, path, state_machine):
        self._sm = state_machine
        self._path = path

    def start(self):
        self._sm.handle_event('start')

    async def start_server(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
        await asyncio.start_unix_server(None, path=self._path)
