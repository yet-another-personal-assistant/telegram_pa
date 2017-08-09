#!/usr/bin/env python3

from tg2sock import Tg2Sock


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Telegram-to-socket connector")
    parser.add_argument("--token-file", default="token.txt", help="Telegram token file")
    Tg2Sock(parser.parse_args()).run()
