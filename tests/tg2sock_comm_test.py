import asyncio
import unittest

from unittest.mock import Mock

from tg2sock import Tg2Sock
from tests.tg2sock_test import AsyncMock, Tg2SockBaseTest


def _build_text_tg_message(text, chat_id):
    return {
        'text': text,
        'chat': {
            'type': 'private',
            'id': chat_id
        }
    }


class Tg2SockCommTest(Tg2SockBaseTest):

    def setUp(self):
        super(Tg2SockCommTest, self).setUp(owner=12345)
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
