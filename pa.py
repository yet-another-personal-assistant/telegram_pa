#!/usr/bin/env python3
import asyncio
import errno
import os
import signal
import sys
import telepot

from telepot.aio.loop import MessageLoop
from time import sleep


_OWNER_ID = None
_bot = None
_FIFO = "pa_fifo"


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
    try:
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        yield from asyncio.get_event_loop().connect_read_pipe(lambda: reader_protocol, sys.stdin)
        while True:
            command = (yield from async_input(reader)).strip()
            print("Got command [{}]".format(command))
            if command == 'stop':
                break
            yield from _bot.sendMessage(_OWNER_ID, "Мне тут пришла команда {}".format(command))
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    _read_config()
    try:
        os.mkfifo(_FIFO)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    loop = asyncio.get_event_loop()
    main_task = asyncio.Task(main())
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, main_task.cancel)
    loop.create_task(MessageLoop(_bot, _handle).run_forever())
    loop.run_until_complete(_bot.sendMessage(_OWNER_ID, "Так, я вернулась"))
    loop.run_until_complete(main_task)
    loop.run_until_complete(_bot.sendMessage(_OWNER_ID, "Мне пора, чмоки!"))
    os.unlink(_FIFO)
