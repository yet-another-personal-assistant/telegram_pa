import asyncio
import logging
import signal
import telepot

from .state import StateMachine
from .local import LocalSocket
from functools import partial
from telepot.aio.loop import MessageLoop

_UNIX = "/tmp/pa_socket"


class Session(object):

    _timer = None

    def __init__(self, bot, chat_id, path, can_stop=False):
        self._logger = logging.getLogger('telepot.{}'.format(chat_id))
        self._bot = bot
        self._backends = []
        self._chat_id = chat_id
        self._can_stop = can_stop
        self._state_machine = StateMachine(self)
        self._server = LocalSocket(self, path)

    def start(self, event='start'):
        self._state_machine.handle_event(event)

    def start_server(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._server.start())

    def stop(self, event='stop'):
        self._state_machine.handle_event(event)
        self._server.stop()

    def remove_client(self, client):
        self._logger.debug("remove client")
        if client in self._backends:
            self._backends.remove(client)
            if not self._backends:
                self._state_machine.handle_event('backend gone')
            self._logger.debug('backend removed, backends left: %d', len(self._backends))

    def send_message(self, message):
        self._logger.debug('sending to remote: "%s"', message)
        loop = asyncio.get_event_loop()
        if message.startswith('message:'):
            actual_message = message[8:].strip()
            if actual_message:
                loop.create_task(self._bot.sendMessage(self._chat_id, actual_message))
        elif message.startswith('picture:'):
            loop.create_task(self._send_picture(message[8:].strip()))
        else:
            loop.create_task(self._bot.sendMessage(self._chat_id, message))

    async def _send_picture(self, file_name):
        with open(file_name, "rb") as photo:
            await self._bot.sendPhoto(self._chat_id, photo)

    async def handle_local(self, command, client):
        self._logger.debug('got from local: "%s"', command)
        if command == 'stop' and self._can_stop:
            asyncio.get_event_loop().stop()
        elif command.startswith('message:'):
            self._state_machine.handle_event('response', command)
        elif command.startswith('picture:'):
            self._state_machine.handle_event('response', command)
        elif command == 'register backend':
            self._backends.insert(0, client)
            if len(self._backends) == 1:
                self._state_machine.handle_event('backend registered')
        self._logger.debug('local message handled')

    def send_to_backend(self, message):
        self._logger.debug('sending to local: "%s"', message)
        self._backends[0].write("message:{}\n".format(message).encode())

    async def handle_remote(self, command):
        self._state_machine.handle_event('message', command)

    def start_timer(self, timeout):
        loop = asyncio.get_event_loop()
        if self._timer is None:
            self._timer = loop.call_later(timeout, self._state_machine.handle_event, 'done')

    def stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


class PersonalAssistant(object):

    def __init__(self, args):
        self._args = args
        self._loop = asyncio.get_event_loop()
        self._friends = set()
        self._ignored = set()
        owner_id = None
        with open(self._args.conf) as token_file:
            for line in token_file:
                key, value = line.strip().split()
                if key == 'TOKEN':
                    self._bot = telepot.aio.Bot(value)
                elif key == 'OWNER':
                    owner_id = int(value)
                elif key == 'FRIEND':
                    self._friends.add(int(value))
        self._sessions = {
            owner_id: Session(self._bot, owner_id, _UNIX, can_stop=True)
        }

    async def _handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if chat_id in self._friends and chat_id not in self._sessions:
            session = Session(self._bot, chat_id, _UNIX+str(chat_id))
            self._sessions[chat_id] = session
            session.start()

        if chat_id in self._sessions and 'text' in msg:
            self._loop.create_task(self._sessions[chat_id].handle_remote(msg['text']))
        else:
            if chat_type == 'private':
                if chat_id not in self._ignored:
                    self._loop.create_task(self._bot.sendMessage(chat_id, "Мы с вами не знакомы"))
                    self._ignored.add(chat_id)
            else:
                self._loop.create_task(self._bot.sendMessage(chat_id, "Я куда-то не туда попалa"))
                self._loop.create_task(self._bot.leaveChat(chat_id))

    def run(self):
        for signame in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(signame, self._loop.stop)

        start_event = 'silent start' if self._args.no_greet else 'owner start'
        for session in self._sessions.values():
            session.start(start_event)

        message_loop = MessageLoop(self._bot, self._handle)
        self._loop.create_task(message_loop.run_forever())
        self._loop.run_forever()
        message_loop.cancel()

        stop_event = 'silent stop' if self._args.no_goodbye else 'stop'
        for session in self._sessions.values():
            session.stop(stop_event)
        pending = asyncio.Task.all_tasks()
        self._loop.run_until_complete(asyncio.gather(*pending))

        print("Ignored: {}".format(self._ignored))
