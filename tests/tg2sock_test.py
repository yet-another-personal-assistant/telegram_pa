import asyncio
import logging
import os
import random
import socket
import stat
import string
import sys
import unittest

from tempfile import mkstemp
from types import SimpleNamespace
from unittest.mock import call, MagicMock, Mock, patch, sentinel

from tg2sock import Tg2Sock


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class Tg2SockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        logging.getLogger('tg2sock').setLevel(logging.DEBUG)
        logging.getLogger('telepot').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)

    def setUp(self):
        self._token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        self._owner = int(''.join(random.choice(string.digits) for _ in range(10)))
        handle, self._path = mkstemp()
        token_handle, self._token_path = mkstemp()
        with os.fdopen(token_handle, "w") as token_file:
            token_file.write("TOKEN {}\nOWNER {}\n".format(self._token, self._owner))
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

        self._bot = Mock()
        self._bot.sendMessage = AsyncMock()
        patcher = patch('telepot.aio.Bot')
        self._botC = patcher.start()
        self._botC.return_value = self._bot
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

        self._botC.assert_called_once_with(self._token)

    def test_run_message_loop(self):
        self._loop.run_until_complete(self._tg2sock.run_forever())

        self._msg_loop.assert_called_once_with(self._bot, self._tg2sock.handle)
        self._msg_loop.return_value.run_forever.assert_called_once_with()

    def test_accept_client(self):
        send_message = self._bot.sendMessage
        reader = Mock()
        writer = Mock()
        reader.readline = AsyncMock(side_effect=['hello'.encode(), 'world'.encode(), 'test'.encode(), ''])
        self._loop.run_until_complete(self._tg2sock.run_forever())
        self.assertEqual(send_message.call_count, 0)

        self._tg2sock.accept_client(reader, writer)

        self._loop.call_later(0.01, self._loop.stop)
        self._loop.run_forever()

        self.assertEqual(send_message.call_count, 3)
        send_message.assert_has_calls([call(self._owner, 'hello'),
                                       call(self._owner, 'world'),
                                       call(self._owner, 'test')])
        writer.close.assert_called_once_with()
