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

    def _make_reader_writer(self, reader_messages=None):
        reader = Mock()
        writer = Mock()
        if reader_messages is not None:
            results = []
            for m in reader_messages:
                if m:
                    results.append("{}\n".format(m).encode())
                else:
                    results.append(''.encode())
            reader.readline = AsyncMock(side_effect=results)
        return reader, writer

    def _make_message(self, text):
        message = Mock()
        def my_get(key, *_):
            return {'text': 'abcd'}[key]
        message.get.side_effect = my_get
        return message

    def _one_async_tick(self):
        self._loop.call_later(0.01, self._loop.stop)
        self._loop.run_forever()

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

    def test_accept_client_messages(self):
        send_message = self._bot.sendMessage
        reader, writer = self._make_reader_writer(['hello', 'world', 'test', ''])

        self._tg2sock.accept_client(reader, writer)

        self._one_async_tick()

        self.assertEqual(send_message.call_count, 3)
        send_message.assert_has_calls([call(self._owner, 'hello'),
                                       call(self._owner, 'world'),
                                       call(self._owner, 'test')])
        writer.close.assert_called_once_with()

    @patch('telepot.glance')
    def test_forward_messages_to_client(self, glance):
        glance.return_value = ('text', 'private', self._owner)
        reader, writer = self._make_reader_writer(['register backend', ''])
        self._loop.run_until_complete(self._tg2sock.run_forever())
        self._tg2sock.accept_client(reader, writer)
        message = Mock()
        def my_get(key, *_):
            return {'text': 'abcd'}[key]
        message.get.side_effect = my_get

        self._tg2sock.handle(message)
        self._one_async_tick()

        glance.assert_called_once_with(message)
        writer.write.assert_called_once_with("chat_id:{},message:abcd\n".format(self._owner).encode())

    @patch('telepot.glance')
    def test_store_client_messages_until_there_is_a_reader(self, glance):
        glance.return_value = ('text', 'private', self._owner)
        reader, writer = self._make_reader_writer(['register backend', ''])
        message = self._make_message('abcd')

        self._tg2sock.handle(message)
        self._one_async_tick()
        glance.assert_called_once_with(message)

        self._tg2sock.accept_client(reader, writer)
        self._one_async_tick()
        writer.write.assert_called_once_with("chat_id:{},message:abcd\n".format(self._owner).encode())

    @patch('telepot.glance')
    def test_dont_send_messages_until_reader_registers_itself_as_backend(self, glance):
        glance.return_value = ('text', 'private', self._owner)
        reader, writer = self._make_reader_writer()
        message = self._make_message('abcd')

        self._tg2sock.handle(message)

        self._tg2sock.accept_client(reader, writer)
        self._one_async_tick()
        writer.write.assert_not_called()

    @patch('telepot.glance')
    def test_multiple_clients(self, glance):
        glance.return_value = ('text', 'private', self._owner)
        reader1, writer1 = self._make_reader_writer(['hello', 'world', ''])
        reader2, writer2 = self._make_reader_writer(['register backend', 'test', ''])
        message = self._make_message('abcd')

        self._tg2sock.handle(message)

        self._tg2sock.accept_client(reader1, writer1)
        self._tg2sock.accept_client(reader2, writer2)
        self._one_async_tick()
        writer1.write.assert_not_called()
        writer2.write.assert_called_once_with("chat_id:{},message:abcd\n".format(self._owner).encode())
