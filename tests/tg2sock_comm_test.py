import asyncio
import logging
import os
import sys
import unittest

from tempfile import mkstemp
from types import SimpleNamespace
from unittest.mock import call, MagicMock, Mock, patch, sentinel

from tg2sock import Tg2Sock


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


def _build_text_tg_message(text, chat_id):
    return {
        'text': text,
        'chat': {
            'type': 'private',
            'id': chat_id
        }
    }


class Tg2SockCommTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        logging.getLogger('tg2sock').setLevel(logging.DEBUG)
        logging.getLogger('telepot').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)

    def setUp(self):
        self._token = "token"
        self._owner = 12345
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
        self._reader = Mock()
        self._writer = Mock()

    def _get_from_tg(self, text, chat_id=None):
        if chat_id is None:
            chat_id = self._owner
        message = _build_text_tg_message(text, chat_id)
        coro = self._tg2sock.handle_remote_message(message)
        self._loop.run_until_complete(coro)

    def _get_from_sock(self, text):
        coro = self._tg2sock.handle_local_message(text, reader=self._reader, writer=self._writer)
        self._loop.run_until_complete(coro)

    def test_send_message(self):
        self._get_from_sock('hello')

        self._bot.sendMessage.assert_called_once_with(self._owner, 'hello')

    def test_get_message(self):
        self._get_from_tg('hello')

    def test_hold_message(self):
        self._get_from_tg('hello')

        self._writer.write.assert_not_called()

        self._get_from_sock('register backend')

        self._writer.write.assert_called_once_with('chat_id:12345,message:hello\n'.encode())

    def test_deliver_message(self):
        self._get_from_sock('register backend')

        self._get_from_tg('hello')

        self._writer.write.assert_called_once_with('chat_id:12345,message:hello\n'.encode())
