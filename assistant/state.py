import asyncio
import logging

class StateMachine(object):

    _logger = None
    _loop = None
    _session = None
    _state = None
    _timer = None

    def __init__(self, session, initial='none'):
        self._logger = logging.getLogger('SM')
        self._loop = asyncio.get_event_loop()
        self._session = session
        self._state = initial
        self._handlers = {
            'none': self._handle_none_state,
            'login': self._handle_login_state,
            'disconnected': self._handle_disconnected_state,
            'disconnected silent': self._handle_disconnected_silent_state,
            'idle': self._handle_idle_state,
        }
        self._logger.info("State machine created")

    @property
    def state(self):
        return self._state

    def _handle_none_state(self, event, _):
        if event == 'start':
            self._loop.create_task(self._session.send_message("Ой, приветик" ))
        elif event == 'owner start':
            self._loop.create_task(self._session.send_message("Так, я вернулась"))
        elif event == 'silent start':
            pass
        else:
            self._unexpected(event)
        self._loop.create_task(self._session.start_server())
        self._start_timer(3)
        return 'login'

    def _handle_login_state(self, event, _):
        self._stop_timer()
        if event == 'message':
            self._loop.create_task(self._session.send_message("Подожди, сейчас прочитаю"))
            self._start_timer(300)
            return 'disconnected silent'
        elif event == 'backend registered':
            return 'idle'
        elif event == 'stop':
            self._loop.create_task(self._session.send_message("Мне пора, чмоки"))
            return 'stop'
        return 'disconnected'

    def _handle_disconnected_state(self, event, _):
        if event == 'message':
            self._loop.create_task(self._session.send_message("Ой, я сейчас по уши занята"))
            self._start_timer(300)
            return 'disconnected silent'
        elif event == 'stop':
            self._loop.create_task(self._session.send_message("Мне пора, чмоки"))
            return 'stop'
        return 'idle'

    def _handle_disconnected_silent_state(self, event, _):
        if event == 'backend registered':
            self._loop.create_task(self._session.send_message("Вот, я слушаю"))
            self._stop_timer()
            return 'idle'
        elif event == 'done':
            return 'disconnected'
        elif event == 'message':
            return 'disconnected silent'
        elif event == 'stop':
            self._loop.create_task(self._session.send_message("Мне пора, чмоки"))
            self._stop_timer()
            return 'stop'
        else:
            self._unexpected(event)

    def _handle_idle_state(self, event, args):
        if event == 'done':
            self._loop.create_task(self._session.send_message("Сейчас подумаю..."))
        elif event == 'message':
            self._loop.create_task(self._session.send_to_backend(*args))
            self._start_timer(5)
        elif event == 'response':
            self._loop.create_task(self._session.send_message(*args))
            self._stop_timer()
        elif event == 'backend gone':
            self._loop.create_task(self._session.send_message("Пойду дальше делами заниматься"))
            self._stop_timer()
            return 'disconnected'
        elif event == 'stop':
            self._loop.create_task(self._session.send_message("Мне пора, чмоки"))
            self._stop_timer()
            return 'stop'
        else:
            self._unexpected(event)
        return 'idle'

    def _unexpected(self, event):
        raise Exception("Unknown event in '{}' state: '{}'".format(self._state, event))

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _start_timer(self, timeout):
        self._timer = self._loop.call_later(timeout, self.handle_event, 'done')

    def handle_event(self, event, *args):
        self._state = self._handlers[self._state](event, args)
        self._logger.debug("State changed to %s", self._state)
