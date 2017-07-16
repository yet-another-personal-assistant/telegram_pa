import asyncio
import os
import unittest

from tempfile import mkstemp
from unittest.mock import MagicMock, Mock, patch, sentinel

from assistant.session import Session


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

class SessionTest(unittest.TestCase):

    def setUp(self):
        self._loop = asyncio.get_event_loop()
        self._bot = Mock()
        self._sm = Mock()
        chat_id = 0
        self._path = str(sentinel.path)
        self._session = Session(self._bot, chat_id, self._path, self._sm)

    def test_start(self):
        self._sm.handle_event.assert_not_called()
        self._session.start()

        self._sm.handle_event.assert_called_once_with('start')

    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_start_server(self, start_server):
        self._loop.run_until_complete(self._session.start_server())

        self.assertEqual(start_server.call_count, 1, "Exactly one server is started")
        self.assertEqual(start_server.call_args[1]['path'], self._path)

    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_start_server_unlink_file(self, start_server):
        path = self._mktemp()

        session = Session(self._bot, 0, path, self._sm)
        self._loop.run_until_complete(session.start_server())

        self.assertEqual(start_server.call_count, 1, "Exactly one server is started")
        self.assertEqual(start_server.call_args[1]['path'], path)
        self.assertFalse(os.path.exists(path))

    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_stop(self, start_server):
        path = self._mktemp()

        session = Session(self._bot, 0, path, self._sm)
        self._loop.run_until_complete(session.start_server())

        self.assertEqual(start_server.call_count, 1, "Exactly one server is started")
        self.assertEqual(start_server.call_args[1]['path'], path)
        self.assertFalse(os.path.exists(path))

    def _mktemp(self):
        fd, path = mkstemp()
        def _deltemp():
            if os.path.exists(path):
                os.unlink(path)
        os.close(fd)
        self.addCleanup(_deltemp)
        return path
