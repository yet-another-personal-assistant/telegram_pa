import asyncio
import os

class Session(object):
    _backend = None
    _server = None
    _path = None
    _bot = None
    _chat_id = None
    _thinking_handle = None
    _can_stop = False

    def __init__(self, bot, chat_id, path, can_stop=False):
        self._path = path
        self._bot = bot
        self._chat_id = chat_id
        self._can_stop = can_stop

    async def start(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
        self._server = await asyncio.start_unix_server(self.accept_client, path=self._path)

    def stop(self):
        os.unlink(self._path)
        self._server.close()

    def write(self, message):
        self._backend.write("message:{}\n".format(message).encode())

    @property
    def can_accept_message(self):
        return self._backend is not None

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

    async def send_msg_async(self, msg):
        await self._bot.sendMessage(self._chat_id, msg)

    def send_msg_sync(self, msg):
        asyncio.get_event_loop().create_task(self.send_msg_async(msg))

    async def _handle_local(self, command, reader, writer):
        if command == 'stop' and self._can_stop:
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

    def i_m_thinking(self):
        self.send_msg_sync("Сейчас подумаю...")

    async def _handle_remote(self, command):
        if self.can_accept_message:
            self.write(command)
            self._thinking_handle = asyncio.get_event_loop().call_later(1, self.i_m_thinking)
        else:
            await self.send_msg_async("Ой, я сейчас по уши занята")
