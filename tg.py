#!/usr/bin/env python3
import argparse
import asyncio

from tg2sock import Tg2Sock


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Telegram-to-socket connector")
    parser.add_argument("--control", default="/tmp/tg_socket", help="Control socket name")
    parser.add_argument("--token-file", default="token.txt", help="Telegram token file")
    loop = asyncio.get_event_loop()
    loop.create_task(Tg2Sock(parser.parse_args()).run_forever())
    loop.run_forever()
