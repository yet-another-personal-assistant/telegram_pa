import asyncio
import os
import signal
import telepot

from telepot.aio.loop import MessageLoop


_UNIX = "/tmp/pa_socket"


class PersonalAssistant(object):
    _OWNER_ID = None
    _args = None
    _bot = None
    _server = None
    _backend = None
    _thinking_handle = None

    def __init__(self):
        import argparse
        parser = argparse.ArgumentParser(description="My Personal Assistant")
        parser.add_argument("--no-greet", action='store_true', help="Skip greeting message")
        parser.add_argument("--no-goodbye", action='store_true', help="Skip goodbye message")
        self._args = parser.parse_args()
        with open("token.txt") as token_file:
            for line in token_file:
                key, value = line.strip().split()
                if key == 'TOKEN':
                    self._bot = telepot.aio.Bot(value)
                elif key == 'OWNER':
                    self._OWNER_ID = int(value)

    def send_msg_sync(self, msg):
        asyncio.get_event_loop().create_task(self.send_msg_async(msg))

    async def send_msg_async(self, msg):
        await self._bot.sendMessage(self._OWNER_ID, msg)

    def i_m_thinking(self):
        self.send_msg_sync("Сейчас подумаю...")

    def accept_client(self, reader, writer):
        task = asyncio.Task(self.handle_client(reader, writer))
        def client_gone(task):
            writer.close()
            if writer == self._backend:
                self._backend = None
                self.send_msg_sync("Пойду дальше делами заниматься")
        task.add_done_callback(client_gone)

    async def handle_client(self, reader, writer):
        while True:
            data = await reader.readline()
            if not data:
                break
            sdata = data.decode().strip()
            if sdata:
                await self._handle_local(sdata, reader, writer)

    async def _handle_local(self, command, reader, writer):
        if command == 'stop':
            asyncio.get_event_loop().stop()
        elif command.startswith('message:'):
            message = command[8:].strip()
            if message:
                if self._thinking_handle is not None:
                    self._thinking_handle.cancel()
                    self._thinking_handle = None
                await self.send_msg_async(message)
        elif command == 'register backend':
            self._backend = writer
            await self.send_msg_async("Вот, я слушаю")

    async def _handle_remote(self, command):
        if self._backend is None:
            await self.send_msg_async("Ой, я сейчас по уши занята")
        else:
            self._backend.write("message:{}\n".format(command).encode())
            self._thinking_handle = asyncio.get_event_loop().call_later(1, self.i_m_thinking)

    async def _handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if chat_id == self._OWNER_ID:
            await self._handle_remote(msg['text'])
        else:
            if chat_type == 'private':
                await self._bot.sendMessage(chat_id, "Мы с вами не знакомы")
            else:
                await self._bot.sendMessage(chat_id, "Я куда-то не туда попалa")
                await self._bot.leaveChat(chat_id)

    async def task(self):
        self._server = await asyncio.start_unix_server(self.accept_client, path=_UNIX)
        await MessageLoop(self._bot, self._handle).run_forever()

    def run(self):
        loop = asyncio.get_event_loop()
        for signame in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signame, loop.stop)
        if os.path.exists(_UNIX):
            os.unlink(_UNIX)
        if not self._args.no_greet:
            self.send_msg_sync("Так, я вернулась")
        loop.create_task(self.task())
        loop.run_forever()
        os.unlink(_UNIX)
        self._server.close()
        if not self._args.no_goodbye:
            loop.run_until_complete(self.send_msg_async("Мне пора, чмоки!"))
