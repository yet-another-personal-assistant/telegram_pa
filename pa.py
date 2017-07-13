#!/usr/bin/env python3
import asyncio
import os
import signal
import telepot

from telepot.aio.loop import MessageLoop


_OWNER_ID = None
_bot = None
_UNIX = "/tmp/pa_socket"
_writer = None


async def send_msg_async(msg):
    await _bot.sendMessage(_OWNER_ID, msg)

def send_msg_sync(msg):
    asyncio.get_event_loop().create_task(send_msg_async(msg))


async def _handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_id == _OWNER_ID:
        if _writer is None
            await _bot.sendMessage(chat_id, "Даже не знаю, что ответить")
        else:
            _writer.write("message:{}\n".format(msg['text']).encode())
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


async def handle_local_command(command, reader, writer):
    if command == 'stop':
        asyncio.get_event_loop().stop()
    elif command.startswith('message:'):
        message = command[8:].strip()
        if message:
            await send_msg_async(message)
    elif command == 'register backend':
        global _writer
        _writer = writer
        await send_msg_async("Вот, я слушаю")


async def handle_client(reader, writer):
    while True:
        data = await reader.readline()
        if not data:
            break
        sdata = data.decode().strip()
        if sdata:
            await handle_local_command(sdata, reader, writer)


def accept_client(reader, writer):
    task = asyncio.Task(handle_client(reader, writer))
    def client_gone(task):
        writer.close()
        global _writer
        if writer == _writer:
            _writer = None
            send_msg_sync("Пойду дальше делами заниматься")
    task.add_done_callback(client_gone)


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="My Personal Assistant")
    parser.add_argument("--no-greet", action='store_true', help="Skip greeting message")
    parser.add_argument("--no-goodbye", action='store_true', help="Skip goodbye message")
    return parser.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    _read_config()
    loop = asyncio.get_event_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signame, loop.stop)
    loop.create_task(MessageLoop(_bot, _handle).run_forever())
    if os.path.exists(_UNIX):
        os.unlink(_UNIX)

    loop.run_until_complete(asyncio.start_unix_server(accept_client, path=_UNIX))
    if not args.no_greet:
        send_msg_sync("Так, я вернулась")
    loop.run_forever()
    if not args.no_goodbye:
        loop.run_until_complete(send_msg_async("Мне пора, чмоки!"))

    os.unlink(_UNIX)
