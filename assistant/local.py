import asyncio
import os

from .backend import BackendConnection


class LocalSocket(object):

    def __init__(self, session, path):
        self._path = path
        self._backends = []
        self._server = None
        self._session = session

    async def start(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
        self._server = await asyncio.start_unix_server(
            self.accept_backend, path=self._path)

    def accept_backend(self, reader, writer):
        backend = BackendConnection(reader, writer, self._session)
        backend.start(asyncio.get_event_loop())
        self._backends.append(backend)

    def stop(self):
        for backend in self._backends:
            backend.close()
        os.unlink(self._path)
        self._server.close()
