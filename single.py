#!/usr/bin/env python3

import asyncio
import logging
import os
import requests
from tg2sock.parser import get_update_id, parse


API_BASE="https://api.telegram.org/bot"


class Tg2Sock(object):

    def __init__(self):
        self._logger = logging.getLogger('tg2sock')
        with open("token.txt") as token_file:
            for line in token_file:
                key, value = line.split()
                if key == "TOKEN":
                    self._uri = API_BASE + value
                elif key == "OWNER":
                    self._owner_id = int(value)
        self._session = requests.Session()
        self._writer = None
        self._offset = None

    async def run_forever(self):
        self._logger.debug("starting server on %s", "control")
        if os.path.exists("control"):
            os.unlink("control")
        await asyncio.start_unix_server(self.accept_client, path="control")
        while True:
            await asyncio.sleep(0.2)
            if self._writer is not None:
                if self._offset is None:
                    r = self._session.get(self._uri+"/getUpdates")
                else:
                    r = self._session.get(self._uri+"/getUpdates", params={'offset':self._offset})
                updates = parse(r.text)
                if updates['ok']:
                    for message in updates['result']:
                        update_id = get_update_id(message)
                        self._writer.write((message+"\n").encode())
                        self._offset = update_id + 1

    def accept_client(self, reader, writer):
        asyncio.Task(self.handle_client(reader, writer))

    def _register_backend(self, writer):
        self._writer = writer

    async def handle_client(self, reader, writer):
        while True:
            sdata = await reader.readline()
            if not sdata:
                break
            await self.handle_local_message(sdata.decode(), reader, writer)
        if writer == self._writer:
            self._writer = None
        writer.close()

    async def handle_local_message(self, message, reader, writer):
        message = message.strip()
        if message == 'register backend':
            self._register_backend(writer)
        elif message:
            self._session.post(self._uri+"/sendMessage", params={'chat_id':self._owner_id,
                                                                 'text':message})


def main():
    tg2sock = Tg2Sock()
    loop = asyncio.get_event_loop()
    loop.create_task(tg2sock.run_forever())
    loop.run_forever()


if __name__ == '__main__':
    main()
