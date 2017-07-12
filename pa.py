#!/usr/bin/env python3
import asyncio
import os
import signal
import telepot

from telepot.aio.loop import MessageLoop


_OWNER_ID = None
_bot = None
_UNIX = "/tmp/pa_socket"


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


async def handle_local_command(command):
    if command == 'stop':
        asyncio.get_event_loop().stop()
    else:
        await _bot.sendMessage(_OWNER_ID, command)


async def handle_client(reader, writer):
    while True:
        data = await reader.readline()
        if not data:
            break
        await handle_local_command(data.decode().strip())


def accept_client(reader, writer):
    task = asyncio.Task(handle_client(reader, writer))
    def client_gone(task):
        writer.close()
    task.add_done_callback(client_gone)


if __name__ == '__main__':
    _read_config()
    loop = asyncio.get_event_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, loop.stop)
    loop.create_task(MessageLoop(_bot, _handle).run_forever())
    if os.path.exists(_UNIX):
        os.unlink(_UNIX)

    loop.run_until_complete(asyncio.start_unix_server(accept_client, path=_UNIX))
    loop.run_until_complete(_bot.sendMessage(_OWNER_ID, "Так, я вернулась"))
    loop.run_forever()
    loop.run_until_complete(_bot.sendMessage(_OWNER_ID, "Мне пора, чмоки!"))

    os.unlink(_UNIX)
