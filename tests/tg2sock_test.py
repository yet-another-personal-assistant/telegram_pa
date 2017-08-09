import asyncio
import logging
import os
import random
import stat
import string
import sys
import unittest

from tempfile import mkstemp
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, sentinel

from tg2sock import Tg2Sock


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class Tg2SockTest(unittest.TestCase):

    _tg2sock = None
    _path = None
    _args = None
    _loop = None
    _token = None
    _token_path = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        logging.getLogger('tg2sock').setLevel(logging.DEBUG)
        logging.getLogger('telepot').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)

    def setUp(self):
        self._token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        handle, self._path = mkstemp()
        token_handle, self._token_path = mkstemp()
        with os.fdopen(token_handle, "w") as token_file:
            token_file.write("TOKEN ")
            token_file.write(self._token)
            token_file.write("\n")
        os.fdopen(handle).close()
        def cleanup():
            if os.path.exists(self._path):
                os.unlink(self._path)
            if os.path.exists(self._token_path):
                os.unlink(self._token_path)
        self.addCleanup(cleanup)
        self._args = SimpleNamespace(control=self._path,
                                     token_file=self._token_path)
        self._loop = asyncio.get_event_loop()

        patcher = patch('telepot.aio.Bot')
        self._bot = patcher.start()
        self._bot.return_value = sentinel.bot
        self.addCleanup(patcher.stop)

        patcher = patch('telepot.aio.loop.MessageLoop')
        self._msg_loop = patcher.start()
        self._msg_loop.return_value.run_forever = AsyncMock()
        self.addCleanup(patcher.stop)

        self._tg2sock = Tg2Sock(self._args)

    def test_create_socket(self):
        self._loop.run_until_complete(self._tg2sock.run_forever())

        stat_result = os.stat(self._path)
        self.assertTrue(stat.S_ISSOCK(stat_result.st_mode))

    @patch('asyncio.start_unix_server', new_callable=AsyncMock)
    def test_accept_callback_passed(self, start_server):
        self._loop.run_until_complete(self._tg2sock.run_forever())

        start_server.assert_called_once_with(
            self._tg2sock.accept_client,
            path=self._path)

    def test_create_bot_with_correct_token(self):
        self._loop.run_until_complete(self._tg2sock.run_forever())

        self._bot.assert_called_once_with(self._token)

    def test_run_message_loop(self):
        self._loop.run_until_complete(self._tg2sock.run_forever())

        self._msg_loop.assert_called_once_with(sentinel.bot, self._tg2sock.handle)
        self._msg_loop.return_value.run_forever.assert_called_once_with()
