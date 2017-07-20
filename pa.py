#!/usr/bin/env python3

from spike.pa import PersonalAssistant


if __name__ == '__main__':
    import argparse
    import logging
    import sys
    parser = argparse.ArgumentParser(description="My Personal Assistant")
    parser.add_argument("--no-greet", action='store_true', help="Skip greeting message")
    parser.add_argument("--no-goodbye", action='store_true', help="Skip goodbye message")
    parser.add_argument("--conf", default="token.txt", help="Configuration file")
    parser.add_argument("--verbose", action='store_true', help="Configuration file")

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger('SM').setLevel(logging.DEBUG)
    logging.getLogger('telepot').setLevel(logging.DEBUG)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    PersonalAssistant(parser.parse_args()).run()
