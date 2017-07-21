import logging

class StateMachine(object):

    _logger = None
    _session = None
    _state = None

    def __init__(self, session, initial='start'):
        self._logger = logging.getLogger('SM')
        self._session = session
        self._state = initial
        self._handlers = {
            'start': self._handle_start_state,
            'login': self._handle_login_state,
            'disconnected': self._handle_disconnected_state,
            'disconnected silent': self._handle_disconnected_silent_state,
            'idle': self._handle_idle_state,
            'stop': self._handle_stop_state,
        }
        self._logger.info("State machine created")

    @property
    def state(self):
        return self._state

    def _handle_stop(self, silent=False):
        if not silent:
            self._session.send_message("Мне пора, чмоки")
        self._session.stop_timer()
        return 'stop'

    def _handle_start_state(self, event, _):
        if event == 'start':
            self._session.send_message("Ой, приветик")
        elif event == 'owner start':
            self._session.send_message("Так, я вернулась")
        elif event == 'silent start':
            pass
        else:
            self._unexpected(event)
        self._session.start_server()
        self._session.start_timer(3)
        return 'login'

    def _handle_login_state(self, event, args):
        self._session.stop_timer()
        if event == 'message':
            self._session.send_message("Подожди, сейчас прочитаю")
            self._session.start_timer(300)
            return 'disconnected silent'
        elif event == 'backend registered':
            return 'idle'
        elif event == 'stop':
            return self._handle_stop()
        elif event == 'silent stop':
            return self._handle_stop(silent=True)
        elif event == 'response':
            self._session.send_message(*args)
            return 'disconnected'
        elif event == 'done':
            return 'disconnected'
        else:
            self._unexpected(event)

    def _handle_disconnected_state(self, event, args):
        if event == 'message':
            self._session.send_message("Ой, я сейчас по уши занята")
            self._session.start_timer(300)
            return 'disconnected silent'
        elif event == 'stop':
            return self._handle_stop()
        elif event == 'silent stop':
            return self._handle_stop(silent=True)
        elif event == 'response':
            self._session.send_message(*args)
            return 'disconnected'
        elif event == 'backend registered':
            return 'idle'
        else:
            self._unexpected(event)

    def _handle_disconnected_silent_state(self, event, args):
        if event == 'backend registered':
            self._session.send_message("Вот, я слушаю")
            self._session.stop_timer()
            return 'idle'
        elif event == 'done':
            return 'disconnected'
        elif event == 'message':
            return 'disconnected silent'
        elif event == 'stop':
            return self._handle_stop()
        elif event == 'silent stop':
            return self._handle_stop(silent=True)
        elif event == 'response':
            self._session.send_message(*args)
            return 'disconnected silent'
        else:
            self._unexpected(event)

    def _handle_idle_state(self, event, args):
        if event == 'done':
            self._session.send_message("Сейчас подумаю...")
        elif event == 'message':
            self._session.send_to_backend(*args)
            self._session.start_timer(5)
        elif event == 'response':
            self._session.send_message(*args)
            self._session.stop_timer()
        elif event == 'backend gone':
            self._session.send_message("Пойду дальше делами заниматься")
            self._session.stop_timer()
            return 'disconnected'
        elif event == 'stop':
            return self._handle_stop()
        elif event == 'silent stop':
            return self._handle_stop(silent=True)
        else:
            self._unexpected(event)
        return 'idle'

    def _handle_stop_state(self, event, _):
        return 'stop'

    def _unexpected(self, event):
        raise Exception("Unknown event in '{}' state: '{}'".format(self._state, event))

    def handle_event(self, event, *args):
        self._logger.debug("Handling event %s in state %s", event, self._state)
        self._state = self._handlers[self._state](event, args)
        self._logger.debug("State changed to %s", self._state)
