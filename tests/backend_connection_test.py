import asyncio
import unittest

from unittest.mock import call, MagicMock, Mock, sentinel

from assistant.backend import BackendConnection


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class BackendConnectionTest(unittest.TestCase):

    _reader = None
    _writer = None
    _session = None
    _backend = None

    def setUp(self):
        self._reader = Mock()
        self._reader.readline = AsyncMock()
        self._writer = Mock()
        self._session = Mock()
        self._session.handle_local = AsyncMock()
        
        self._backend = BackendConnection(self._reader, self._writer, self._session)

    def test_start(self):
        real_loop = asyncio.get_event_loop()
        loop = Mock()
        def create(coro):
            self._task = real_loop.create_task(coro)
            return self._task
        loop.create_task = MagicMock(side_effect=create)
        self._reader.readline.side_effect = [b"line\n", b""]

        self._backend.start(loop)
        real_loop.run_until_complete(self._task)

        self._session.handle_local.assert_called_once_with("line", self._backend)
        self._writer.close.assert_called_once_with()
        self._session.remove_client.assert_called_once_with(self._backend)
        self.assertFalse(self._task.cancelled())

    def test_run_forever(self):
        loop = asyncio.get_event_loop()
        self._reader.readline.side_effect = [b"One\n",
                                             b"\xd0\x94\xd0\xb2\xd0\xb0\n",
                                             b"\xe4\xb8\x89\n",
                                             b"\n",
                                             b""]

        task = loop.create_task(self._backend.run_forever())
        loop.run_until_complete(task)

        self.assertEquals(self._session.handle_local.call_count, 3)
        self._session.handle_local.assert_has_calls(
            [call("One", self._backend),
             call("Два", self._backend),
             call("三", self._backend)])

    def test_write(self):
        self._backend.write(sentinel.message)

        self._writer.write.assert_called_once_with(sentinel.message)

    def test_direct_close(self):
        real_loop = asyncio.get_event_loop()
        loop = Mock()
        def create(coro):
            self._task = real_loop.create_task(coro)
            return self._task
        loop.create_task = MagicMock(side_effect=create)
        class MockReader(MagicMock):
            async def __call__(self, *args, **kwargs):
                await asyncio.sleep(10)
                raise Exception("Not cancelled")
        self._reader.readline = MockReader()

        self._backend.start(loop)
        real_loop.call_soon(self._backend.close)
        real_loop.run_until_complete(self._task)

        self._session.remove_client.assert_called_once_with(self._backend)
        self._writer.close.assert_called_once_with()
