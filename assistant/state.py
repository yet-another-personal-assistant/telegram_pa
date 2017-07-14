import asyncio

class StateMachine(object):

    _session = None
    _state = None
    _timer = None

    def __init__(self, session, initial='none'):
        self._session = session
        self._state = initial
        self._handlers = {
            'none': self._handle_none_state,
            'login': self._handle_login_state,
            'disconnected': self._handle_disconnected_state,
            'disconnected silent': self._handle_disconnected_silent_state,
        }

    @property
    def state(self):
        return self._state

    def _handle_none_state(self, event):
        loop = asyncio.get_event_loop()
        if event == 'start':
            loop.create_task(self._session.send_message("Ой, приветик" ))
        elif event == 'owner start':
            loop.create_task(self._session.send_message("Так, я вернулась"))
        elif event == 'silent start':
            pass
        else:
            self._unexpected(event)
        loop.create_task(self._session.start_server())
        self._timer = loop.call_later(3, self.handle_event, 'done')
        return 'login'

    def _handle_login_state(self, event):
        loop = asyncio.get_event_loop()
        if event == 'message':
            loop.create_task(self._session.send_message("Подожди, сейчас прочитаю"))
            self._timer = loop.call_later(300, self.handle_event, 'done')
            return 'disconnected silent'
        if event == 'backend registered':
            self._timer.cancel()
            return 'idle'
        return 'disconnected'

    def _handle_disconnected_state(self, event):
        loop = asyncio.get_event_loop()
        if event == 'message':
            loop.create_task(self._session.send_message("Ой, я сейчас по уши занята"))
            self._timer = loop.call_later(300, self.handle_event, 'done')
            return 'disconnected silent'
        return 'idle'

    def _handle_disconnected_silent_state(self, event):
        loop = asyncio.get_event_loop()
        if event == 'backend registered':
            loop.create_task(self._session.send_message("Вот, я слушаю"))
            self._timer.cancel()
            return 'idle'
        elif event == 'done':
            return 'disconnected'
        elif event == 'message':
            return 'disconnected silent'
        else:
            self._unexpected(event)

    def _unexpected(self, event):
        raise Exception("Unknown event in '{}' state: '{}'".format(self._state, event))

    def handle_event(self, event, *args):
        self._state = self._handlers[self._state](event)
    
