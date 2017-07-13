#!/usr/bin/env python3

from assistant import PersonalAssistant


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="My Personal Assistant")
    parser.add_argument("--no-greet", action='store_true', help="Skip greeting message")
    parser.add_argument("--no-goodbye", action='store_true', help="Skip goodbye message")
    parser.add_argument("--conf", default="token.txt", help="Configuration file")
    PersonalAssistant(parser.parse_args()).run()
