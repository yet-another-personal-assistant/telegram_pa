#!/usr/bin/env python3
import telepot
from time import sleep

_OWNER_ID = None


def handle(msg):
    print("Got something")
    content_type, chat_type, chat_id = telepot.glance(msg)
    print("Channel type", chat_type)
    if chat_id != _OWNER_ID:
        if chat_type == 'private':
            bot.sendMessage(chat_id, 'Мы с вами не знакомы')
        else:
            bot.sendMessage(chat_id, "Я куда-то не туда попалa")
        bot.leaveChat(chat_id)
        return
    bot.sendMessage(chat_id, "Даже не знаю, что ответить")


if __name__ == '__main__':
    with open("token.txt") as token_file:
        for line in token_file:
            key, value = line.strip().split()
            if key == 'TOKEN':
                token = value
            elif key == 'OWNER':
                _OWNER_ID = int(value)
    bot = telepot.Bot(token)
    bot.message_loop(handle)
    while True:
        sleep(100)
