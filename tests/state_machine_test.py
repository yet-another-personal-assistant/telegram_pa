import asyncio
import unittest

from unittest.mock import call, Mock, patch, sentinel

from assistant.state import StateMachine
    

@unittest.skip
class StateMachineTest(unittest.TestCase):

    _loop = None
    _session = None
    _call_later = None
    _create_task = None

    def setUp(self):
        self._loop = asyncio.get_event_loop()
        self.addCleanup(self._loop.stop)

        patcher = patch.object(self._loop, 'call_later')
        self._call_later = patcher.start()
        self.addCleanup(self._call_later.stop)
        patcher = patch.object(self._loop, 'create_task')
        self._create_task = patcher.start()
        self.addCleanup(self._create_task.stop)

        self._session = Mock()
        self._session.start_server.return_value = sentinel.start_server
        self._session.send_message.return_value = sentinel.send_message
        self._session.send_to_backend.return_value = sentinel.send_to_backend

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
        machine = StateMachine(self._session)
        machine.handle_event('silent start')
        timer = self._call_later.return_value

        machine.handle_event('message', 'hello')
        
        self._session.send_message.assert_called_once_with("Подожди, сейчас прочитаю")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'disconnected silent', "Quietly expecting backend")
        self._call_later.assert_any_call(300, machine.handle_event, 'done')
        self.assertTrue(timer.cancel.called, "Cancel timer")

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

    def test_message_when_idle(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('message', sentinel.message)

        self._session.send_message.assert_not_called()
        self._session.send_to_backend.assert_called_once_with(sentinel.message)
        self._create_task.assert_any_call(sentinel.send_to_backend)
        self.assertEqual(machine.state, 'idle', "Waiting for more messages")
        self._call_later.assert_any_call(5, machine.handle_event, 'done')

    def test_message_timeout(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('done')

        self._session.send_message.assert_called_once_with("Сейчас подумаю...")
        self._create_task.assert_any_call(sentinel.send_message)
        self._session.send_to_backend.assert_not_called()
        self.assertEqual(machine.state, 'idle', "Awaiting messages")

    def test_message_response(self):
        machine = StateMachine(self._session, 'idle')
        machine.handle_event('message', sentinel.message)
        self._create_task.reset_mock()
        timer = self._call_later.return_value

        machine.handle_event('response', sentinel.response)

        self._session.send_message.assert_called_once_with(sentinel.response)
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_backend_disconnect(self):
        machine = StateMachine(self._session, 'idle')
        machine.handle_event('message', sentinel.message)
        self._create_task.reset_mock()
        timer = self._call_later.return_value

        machine.handle_event('backend gone')

        self._session.send_message.assert_called_once_with("Пойду дальше делами заниматься")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'disconnected', "Waiting for backend to reconnect")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_stop_during_login(self):
        machine = StateMachine(self._session)
        machine.handle_event('silent start')
        timer = self._call_later.return_value

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'stop', "Stopped")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_stop_when_disconnected(self):
        machine = StateMachine(self._session, 'disconnected')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'stop', "Stopped")

    def test_stop_when_disconnected_silent(self):
        machine = StateMachine(self._session, 'disconnected')
        machine.handle_event('message', sentinel.message)
        timer = self._call_later.return_value
        self._create_task.reset_mock()
        self._session.send_message.reset_mock()

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'stop', "Stopped")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_stop_when_idle(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'stop', "Stopped")

    def test_stop_when_idle_thinking(self):
        machine = StateMachine(self._session, 'idle')
        machine.handle_event('message', sentinel.message)
        timer = self._call_later.return_value
        self._create_task.reset_mock()
        self._session.send_message.reset_mock()

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self._create_task.assert_any_call(sentinel.send_message)
        self.assertEqual(machine.state, 'stop', "Stopped")
        self.assertTrue(timer.cancel.called, "Cancel timer")

    def test_unexpected(self):
        machine1 = StateMachine(self._session, 'idle')
        machine2 = StateMachine(self._session, 'disconnected silent')

        with self.assertRaisesRegex(Exception, "Unknown event in 'idle' state: 'start'"):
            machine1.handle_event('start')

        with self.assertRaisesRegex(Exception,
                                    "Unknown event in 'disconnected silent' state: 'start'"):
            machine2.handle_event('start')
