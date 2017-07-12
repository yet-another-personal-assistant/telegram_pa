#!/usr/bin/env python3
import asyncio
import os
import signal
import sys
import telepot

from telepot.aio.loop import MessageLoop
from time import sleep


_OWNER_ID = None
_bot = None


@asyncio.coroutine
def async_input(reader):
    line = yield from reader.readline()
    return line.decode('utf8').replace('\r', '').replace('\n', '')


async def _handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_id == _OWNER_ID:
        await _bot.sendMessage(chat_id, "Даже не знаю, что ответить")
    else:
        if chat_type == 'private':
            await _bot.sendMessage(chat_id, "Мы с вами не знакомы")
        else:
            await _bot.sendMessage(chat_id, "Я куда-то не туда попалa")
        await _bot.leaveChat(chat_id)


def _read_config():
    global _OWNER_ID, _bot
    with open("token.txt") as token_file:
        for line in token_file:
            key, value = line.strip().split()
            if key == 'TOKEN':
                _bot = telepot.aio.Bot(value)
            elif key == 'OWNER':
                _OWNER_ID = int(value)


@asyncio.coroutine
def main():
    reader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(reader)
    yield from asyncio.get_event_loop().connect_read_pipe(lambda: reader_protocol, sys.stdin)
    while True:
        command = (yield from async_input(reader)).strip()
        print("Got command [{}]".format(command))
        if command == 'stop':
            break
        yield from _bot.sendMessage(_OWNER_ID, "Мне тут пришла команда {}".format(command))
    yield from _bot.sendMessage(_OWNER_ID, "Мне пора, чмоки!")


if __name__ == '__main__':
    _read_config()
    loop = asyncio.get_event_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, loop.stop)
    loop.create_task(MessageLoop(_bot, _handle).run_forever())
    loop.run_until_complete(main())
