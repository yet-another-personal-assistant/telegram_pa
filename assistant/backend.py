import asyncio

class BackendConnection(object):

    def __init__(self, reader, writer, session):
        self._task = None
        self._reader = reader
        self._writer = writer
        self._session = session

    def start(self, loop):
        self._task = loop.create_task(self.run_forever())
        self._task.add_done_callback(self._close)

    async def run_forever(self):
        try:
            while True:
                sdata = await self._reader.readline()
                if not sdata:
                    break
                data = sdata.decode().strip()
                if data:
                    await self._session.handle_local(data, self)
        except asyncio.CancelledError:
            pass

    def write(self, message):
        self._writer.write(message)

    def _close(self, task):
        self._session.remove_client(self)
        self._writer.close()

    def close(self):
        self._task.cancel()
