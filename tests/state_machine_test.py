import unittest

from unittest.mock import Mock, sentinel

from assistant.state import StateMachine
    

class StateMachineTest(unittest.TestCase):

    _session = None

    def setUp(self):
        self._session = Mock()

    def test_initial_state(self):
        self.assertEqual(StateMachine(Mock()).state, 'start', "Initial state is start")

    def test_different_initial_state(self):
        machine = StateMachine(Mock(), initial='login')
        self.assertEqual(machine.state, 'login', "Can set any initial state")

    def test_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('start')

        self._session.send_message.assert_called_once_with("Ой, приветик")
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._session.start_timer.assert_any_call(3)

    def test_owner_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('owner start')

        self._session.send_message.assert_called_once_with("Так, я вернулась")
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._session.start_timer.assert_any_call(3)

    def test_silent_start_sequence(self):
        machine = StateMachine(self._session)

        machine.handle_event('silent start')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'login', "Tried to greet and proceeded")
        self._session.start_timer.assert_any_call(3)

    def test_message_in_start_state(self):
        machine = StateMachine(self._session)

        with self.assertRaisesRegex(Exception, "Unknown event in 'start' state: 'message'"):
            machine.handle_event('message', 'hello')

    def test_get_message_during_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('message', 'hello')
        
        self._session.send_message.assert_called_once_with("Подожди, сейчас прочитаю")
        self.assertEqual(machine.state, 'disconnected silent', "Quietly expecting backend")
        self._session.stop_timer.assert_called_once_with()
        self._session.start_timer.assert_called_once_with(300)

    def test_3_seconds_passed_after_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('done')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'disconnected', "Expecting backend")

    def test_got_backend_on_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('backend registered')

        self._session.send_message.assert_not_called()
        self._session.stop_timer.assert_called_once_with()
        self.assertEqual(machine.state, 'idle', "Expecting messages")

    def test_got_message_no_backend(self):
        machine = StateMachine(self._session, 'disconnected')
        
        machine.handle_event('message', 'hello')
        
        self._session.send_message.assert_called_once_with("Ой, я сейчас по уши занята")
        self.assertEqual(machine.state, 'disconnected silent', "Quietly expecting backend")
        self._session.start_timer.assert_called_once_with(300)

    def test_got_backend(self):
        machine = StateMachine(self._session, 'disconnected')

        machine.handle_event('backend registered')

        self._session.send_message.assert_not_called()
        self.assertEqual(machine.state, 'idle', "Awaiting messages")

    def test_got_backend_when_silent_from_initial_message(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('backend registered')
        
        self._session.send_message.assert_called_once_with("Вот, я слушаю")
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self._session.stop_timer.assert_called_once_with()

    def test_got_backend_when_silent(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('backend registered')
        
        self._session.send_message.assert_called_once_with("Вот, я слушаю")
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self._session.stop_timer.assert_called_once_with()

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
        self.assertEqual(machine.state, 'idle', "Waiting for more messages")
        self._session.start_timer.assert_called_once_with(5)

    def test_message_timeout(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('done')

        self._session.send_message.assert_called_once_with("Сейчас подумаю...")
        self._session.send_to_backend.assert_not_called()
        self.assertEqual(machine.state, 'idle', "Awaiting messages")

    def test_message_response(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('response', sentinel.response)

        self._session.send_message.assert_called_once_with(sentinel.response)
        self.assertEqual(machine.state, 'idle', "Awaiting messages")
        self._session.stop_timer.assert_called_once_with()

    def test_response_login(self):
        machine = StateMachine(self._session, 'login')

        machine.handle_event('response', sentinel.response)

        self._session.send_message.assert_called_once_with(sentinel.response)
        self.assertEqual(machine.state, 'disconnected')
        self._session.stop_timer.assert_called_once_with()

    def test_response_disconnected(self):
        machine = StateMachine(self._session, 'disconnected')

        machine.handle_event('response', sentinel.response)

        self._session.send_message.assert_called_once_with(sentinel.response)
        self.assertEqual(machine.state, 'disconnected')

    def test_response_disconnected_silent(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('response', sentinel.response)

        self._session.send_message.assert_called_once_with(sentinel.response)
        self.assertEqual(machine.state, 'disconnected silent')

    def test_backend_disconnect(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('backend gone')

        self._session.send_message.assert_called_once_with("Пойду дальше делами заниматься")
        self.assertEqual(machine.state, 'disconnected', "Waiting for backend to reconnect")
        self._session.stop_timer.assert_called_once_with()

    def test_stop_during_login(self):
        machine = StateMachine(self._session, initial='login')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self.assertEqual(machine.state, 'stop', "Stopped")
        self._session.stop_timer.assert_called_once_with()

    def test_stop_when_disconnected(self):
        machine = StateMachine(self._session, 'disconnected')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self.assertEqual(machine.state, 'stop', "Stopped")

    def test_stop_when_disconnected_silent(self):
        machine = StateMachine(self._session, 'disconnected silent')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self.assertEqual(machine.state, 'stop', "Stopped")
        self._session.stop_timer.assert_called_once_with()

    def test_stop_when_idle(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self.assertEqual(machine.state, 'stop', "Stopped")

    def test_stop_when_idle_thinking(self):
        machine = StateMachine(self._session, 'idle')

        machine.handle_event('stop')

        self._session.send_message.assert_called_once_with("Мне пора, чмоки")
        self.assertEqual(machine.state, 'stop', "Stopped")
        self._session.stop_timer.assert_called_once_with()

    def test_unexpected(self):
        for state in ['idle', 'login', 'disconnected', 'disconnected silent']:
            with self.assertRaisesRegex(Exception,
                                        "Unknown event in '{}' state: 'start'".format(state)):
                StateMachine(self._session, initial=state).handle_event('start')
