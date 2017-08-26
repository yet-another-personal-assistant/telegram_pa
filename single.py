#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import telepot.aio


API_BASE="https://api.telegram.org/bot"


class Tg2Sock(object):

    def __init__(self):
        self._logger = logging.getLogger('tg2sock')
        with open("token.txt") as token_file:
            for line in token_file:
                key, value = line.split()
                if key == "TOKEN":
                    self._bot = telepot.aio.Bot(value)
                    self._uri = API_BASE + value
                elif key == "OWNER":
                    self._owner_id = int(value)
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
                # telepot getUpdates gets a string then parses it as json
                # It only actually needs some keys from it and the rest is passed to me
                # I do not need full messages, so I have to convert it back to string
                # If current approach becomes a bottleneck, I should get updates myself:
                # - use aiohttp to fetch api result
                # - use my parser (parser.parse) to only process simple keys and lists
                # - use get_update_id to get the update_id from unparsed-json message
                updates = await self._bot.getUpdates(offset=self._offset)
                for message in updates:
                    self._writer.write((json.dumps(message)+"\n").encode())
                    self._offset = message['update_id'] + 1

    def accept_client(self, reader, writer):
        asyncio.Task(self.handle_client(reader, writer))

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
            self._writer = writer
        elif message:
            await self._bot.sendMessage(self._owner_id, message)


def main():
    tg2sock = Tg2Sock()
    loop = asyncio.get_event_loop()
    loop.create_task(tg2sock.run_forever())
    loop.run_forever()


if __name__ == '__main__':
    main()
