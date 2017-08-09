import asyncio
import logging
import os
import stat
import sys
import unittest

from tempfile import mkstemp
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tg2sock import Tg2Sock


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class Tg2SockTest(unittest.TestCase):

    _tg2sock = None
    _path = None
    _args = None
    _loop = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        logging.getLogger('tg2sock').setLevel(logging.DEBUG)
        logging.getLogger('telepot').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)

    def setUp(self):
        handle, self._path = mkstemp()
        os.fdopen(handle).close()
        def cleanup():
            if os.path.exists(self._path):
                os.unlink(self._path)
        self.addCleanup(cleanup)
        self._args = SimpleNamespace(control=self._path)
        self._tg2sock = Tg2Sock(self._args)
        self._loop = asyncio.get_event_loop()

    def test_start(self):
        self._loop.run_until_complete(self._tg2sock.start())

        stat_result = os.stat(self._path)
        self.assertTrue(stat.S_ISSOCK(stat_result.st_mode))

    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_accept_callback_passed(self, start_server):
        self._loop.run_until_complete(self._tg2sock.start())

        start_server.assert_called_once_with(
            self._tg2sock.accept_client,
            path=self._path)
