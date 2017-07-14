import asyncio
import logging
import unittest

from unittest.mock import call, Mock, MagicMock, patch, sentinel

from assistant.state import StateMachine


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
    

class StateMachineTest(unittest.TestCase):

    _loop = None
    _session = None
    _call_later = None
    _create_task = None

    @classmethod
    def setUpClass(cls):
        logging.getLogger('asyncio').setLevel(logging.WARNING)

    def setUp(self):
        self._loop = asyncio.get_event_loop()
        self.addCleanup(self._loop.stop)
        self._loop.set_debug(True)

        patcher = patch.object(self._loop, 'call_later')
        self._call_later = patcher.start()
        self.addCleanup(self._call_later.stop)
        patcher = patch.object(self._loop, 'create_task')
        self._create_task = patcher.start()
        self.addCleanup(self._create_task.stop)

        self._session = Mock()
        self._session.start_server.return_value = sentinel.start_server
        self._session.send_message.return_value = sentinel.send_message

    def test_initial_state(self):
        self.assertEqual(StateMachine(Mock()).state, 'none', "Initial state is none")

    def test_different_initial_state(self):
        machine = StateMachine(Mock(), initial='login')
        self.assertEqual(machine.state, 'login', "Can set any initial state")

    def test_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('start')

        self._session.send_message.assert_called_once_with("Ой, приветик")
        self._create_task.assert_any_call(sentinel.send_message)
        self._create_task.assert_any_call(sentinel.start_server)
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._call_later.assert_any_call(3, machine.handle_event, 'done')

    def test_owner_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('owner start')

        self._session.send_message.assert_called_once_with("Так, я вернулась")
        self._create_task.assert_any_call(sentinel.send_message)
        self._create_task.assert_any_call(sentinel.start_server)
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._call_later.assert_any_call(3, machine.handle_event, 'done')

    def test_silent_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('silent start')

        self._session.send_message.assert_not_called()
        self._create_task.assert_any_call(sentinel.start_server)
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._call_later.assert_any_call(3, machine.handle_event, 'done')

    def test_message_in_none_state(self):
        machine = StateMachine(self._session)

        with self.assertRaisesRegex(Exception, "Unknown event in 'none' state: 'message'"):
            machine.handle_event('message', 'hello')

    def test_get_message_during_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('message', 'hello')
        
        self._session.send_message.assert_called_once_with("Подожди, сейчас прочитаю")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'disconnected silent', "Quietly expecting backend")
        self._call_later.assert_any_call(300, machine.handle_event, 'done')

    def test_3_seconds_passed_after_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('done')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'disconnected', "Expecting backend")

    def test_got_backend_on_login(self):
        machine = StateMachine(self._session)
        machine.handle_event('silent start')
        timer = self._call_later.return_value

        machine.handle_event('backend registered')

        self._session.send_message.assert_not_called()
        self.assertTrue(timer.cancel.called, "Cancel timer")
        self.assertEqual(machine.state, 'idle', "Expecting messages")

    def test_got_message_no_backend(self):
        machine = StateMachine(self._session, 'disconnected')
        
        machine.handle_event('message', 'hello')
        
        self._session.send_message.assert_called_once_with("Ой, я сейчас по уши занята")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'disconnected silent', "Quietly expecting backend")
        self._call_later.assert_any_call(300, machine.handle_event, 'done')

    def test_got_backend(self):
        machine = StateMachine(self._session, 'disconnected')

        machine.handle_event('backend registered')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'idle', "Awaiting messages")

    def test_got_backend_when_silent_from_initial_message(self):
        machine = StateMachine(self._session, 'login')
        machine.handle_event('message', 'hello')
        self._session.send_message.reset_mock()
        self._create_task.reset_mock()
        timer = self._call_later.return_value

        machine.handle_event('backend registered')
        
        self._session.send_message.assert_called_once_with("Вот, я слушаю")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_got_backend_when_silent(self):
        machine = StateMachine(self._session, 'disconnected')
        machine.handle_event('message', 'hello')
        self._session.send_message.reset_mock()
        self._create_task.reset_mock()
        timer = self._call_later.return_value

        machine.handle_event('backend registered')
        
        self._session.send_message.assert_called_once_with("Вот, я слушаю")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_message_when_silent(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('message', 'hello')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'disconnected silent', "Nothing changed")

    def test_timeout_when_silent(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('done')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'disconnected', "Can speak again")
