import asyncio
import os
import stat
import unittest

from tempfile import mkstemp
from unittest.mock import call, MagicMock, Mock, patch, sentinel

from assistant.local import LocalSocket

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class LocalSocketTest(unittest.TestCase):

    _path = None

    def setUp(self):
        handle, self._path = mkstemp()
        os.fdopen(handle).close()
        def cleanup():
            if os.path.exists(self._path):
                os.unlink(self._path)
        self.addCleanup(cleanup)

    def test_start(self):
        local_socket = LocalSocket(None, self._path)
        loop = asyncio.get_event_loop()

        loop.run_until_complete(local_socket.start())

        stat_result = os.stat(self._path)
        self.assertTrue(stat.S_ISSOCK(stat_result.st_mode))


    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_accept_callback_passed(self, start_server):
        local_socket = LocalSocket(None, self._path)
        loop = asyncio.get_event_loop()
        
        loop.run_until_complete(local_socket.start())

        start_server.assert_called_once_with(
            local_socket.accept_backend,
            path=self._path)

    def test_stop(self):
        server = Mock()
        patcher = patch('asyncio.start_unix_server',
                        new_callable=AsyncMock,
                        return_value=server)
        self.addCleanup(patcher.stop)
        start_server = patcher.start()
        local_socket = LocalSocket(None, self._path)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(local_socket.start())
        open(self._path, 'a').close()

        local_socket.stop()

        server.close.assert_called_once_with()
        self.assertFalse(os.path.exists(self._path))

    @patch('asyncio.start_unix_server', new_callable=AsyncMock,
           return_value=Mock())
    @patch('assistant.local.BackendConnection')
    def test_accept_backend(self, backend, start_server):
        local_socket = LocalSocket(sentinel.session, self._path)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(local_socket.start())
        open(self._path, 'a').close()
        
        local_socket.accept_backend(sentinel.rd1, sentinel.wr1)
        backend.return_value.start.assert_called_once_with(loop)
        local_socket.accept_backend(sentinel.rd2, sentinel.wr2)

        self.assertEqual(backend.call_args_list,
                         [call(sentinel.rd1, sentinel.wr1, sentinel.session),
                          call(sentinel.rd2, sentinel.wr2, sentinel.session)])

        local_socket.stop()
        self.assertEqual(backend.return_value.close.call_count, 2)
