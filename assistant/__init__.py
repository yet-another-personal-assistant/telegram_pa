import asyncio
import signal
import telepot

from telepot.aio.loop import MessageLoop

from assistant.session import Session


_UNIX = "/tmp/pa_socket"


class PersonalAssistant(object):
    _args = None
    _bot = None
    _sessions = None
    _friends = None
    _ignored = None

    def __init__(self, args):
        self._friends = set()
        self._ignored = set()
        self._args = args
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
        if chat_id in self._sessions:
            await self._sessions[chat_id]._handle_remote(msg['text'])
        elif chat_id in self._friends:
            session = Session(self._bot, chat_id, _UNIX+str(chat_id))
            self._sessions[chat_id] = session
            await session.start()
            session.send_msg_sync("Ой, приветик")
            await session._handle_remote(msg['text'])
        else:
            if chat_type == 'private':
                if chat_id not in self._ignored:
                    await self._bot.sendMessage(chat_id, "Мы с вами не знакомы")
                    self._ignored.add(chat_id)
            else:
                await self._bot.sendMessage(chat_id, "Я куда-то не туда попалa")
                await self._bot.leaveChat(chat_id)

    async def task(self):
        await MessageLoop(self._bot, self._handle).run_forever()

    def run(self):
        loop = asyncio.get_event_loop()
        for signame in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signame, loop.stop)

        tasks = [s.start() for s in self._sessions.values()]
        loop.run_until_complete(asyncio.gather(*tasks))
        if not self._args.no_greet:
            for session in self._sessions.values():
                session.send_msg_sync("Так, я вернулась")

        loop.create_task(self.task())
        loop.run_forever()

        for session in self._sessions.values():
            session.stop()
        if not self._args.no_goodbye:
            tasks = [s.send_msg_async("Мне пора, чмоки!") for s in self._sessions.values()]
            loop.run_until_complete(asyncio.gather(*tasks))

        print("Ignored: {}".format(self._ignored))
