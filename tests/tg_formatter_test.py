import json
import unittest

from tg2sock import msg2str
from tests.tg2sock_test import build_text_tg_message


@unittest.skip
class TgFormatterTest(unittest.TestCase):

    def test_format(self):
        msg = build_text_tg_message(12345, "hello")
        self.assertEqual(msg2str(msg), json.dumps(msg))

    def test_format_cyrillic(self):
        msg = build_text_tg_message(12345, "привет")
        self.assertEqual(msg2str(msg), json.dumps(msg, ensure_ascii=False))
