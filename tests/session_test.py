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
        self._bot.sendMessage = AsyncMock()
        self._sm = Mock()
        chat_id = sentinel.chat_id
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

    @patch('asyncio.start_unix_server', new_callable=AsyncMock, return_value=Mock())
    def test_stop(self, start_server):
        path = self._mktemp()
        session = Session(self._bot, 0, path, self._sm)
        self._loop.run_until_complete(session.start_server())
        open(path, 'a').close()

        session.stop()

        start_server.return_value.close.assert_called_once_with()
        self.assertFalse(os.path.exists(path))

    def test_send_message(self):
        self._loop.run_until_complete(self._session.send_message(sentinel.message))

        self._bot.sendMessage.assert_called_once_with(sentinel.chat_id, sentinel.message)

    def test_handle_remote(self):
        self._loop.run_until_complete(self._session.handle_remote(sentinel.message))

        self._sm.handle_event.assert_called_once_with('message', sentinel.message)

    @patch('asyncio.Task')
    def test_accept_client(self, task):
        accept_client = self._get_accept_client_method(self._session)
        writer = Mock()

        accept_client(sentinel.reader, writer)

        self.assertTrue(task.called, "Task was created")
        self.assertTrue(task.return_value.add_done_callback.called,
                        "There is cleanup callback for client")
        cleanup_callback = task.return_value.add_done_callback.call_args[0][0]

        accept_client(sentinel.reader, Mock())

        writer.close.assert_not_called()

        cleanup_callback(task.return_value)
        writer.close.assert_called_once_with()


    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def _get_accept_client_method(self, session, start_server):
        self._loop.run_until_complete(self._session.start_server())
        return start_server.call_args[0][0]

    def _mktemp(self):
        fd, path = mkstemp()
        def _deltemp():
            if os.path.exists(path):
                os.unlink(path)
        os.close(fd)
        self.addCleanup(_deltemp)
        return path
