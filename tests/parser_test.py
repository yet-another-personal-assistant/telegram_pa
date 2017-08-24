import unittest

import tg2sock.parser

from tg2sock.parser import get_update_id, parse


class ParserTest(unittest.TestCase):

    def test_parse_empty(self):
        updates_text = '''{"ok":true,"result":[]}'''

        updates = parse(updates_text)

        self.assertEqual(updates['ok'], True)
        self.assertEqual(updates['result'], [])

    def test_parse_one(self):
        message_text = '''{"update_id":1234,
"message":{"message_id":1,"from":{"id":12345,"is_bot":false,"first_name":"Name","username":"user","language_code":"en-US"},"chat":{"id":1234,"first_name":"Name","username":"user","type":"private"},"date":0,"text":"test"}}'''
        updates_text = '{"ok":true,"result":['+message_text+']}'

        updates = parse(updates_text)

        self.assertEqual(updates['ok'], True)
        self.assertEqual(updates['result'], [message_text.translate(str.maketrans('\n', ' '))])

    def test_parse_two(self):
        messages = ['''{"update_id":1234,
"message":{"message_id":1,"from":{"id":12345,"is_bot":false,"first_name":"Name","username":"user","language_code":"en-US"},"chat":{"id":1234,"first_name":"Name","username":"user","type":"private"},"date":0,"text":"test"}}''',
                    '''{"update_id":1235,
"message":{"message_id":1,"from":{"id":12345,"is_bot":false,"first_name":"Name","username":"user","language_code":"en-US"},"chat":{"id":1234,"first_name":"Name","username":"user","type":"private"},"date":0,"text":"test2"}}''']
        updates_text = '{"ok":true,"result":['+",".join(messages)+']}'

        updates = parse(updates_text)

        translate = str.maketrans('\n', ' ')
        self.assertEqual(updates['ok'], True)
        self.assertEqual(updates['result'], [messages[0].translate(translate),
                                             messages[1].translate(translate)])


class UpdateIdTest(unittest.TestCase):

    def test_correct(self):
        message_text = '''{"update_id":1234,
"message":{"message_id":1,"from":{"id":12345,"is_bot":false,"first_name":"Name","username":"user","language_code":"en-US"},"chat":{"id":1234,"first_name":"Name","username":"user","type":"private"},"date":0,"text":"test"}}'''

        update_id = get_update_id(message_text)

        self.assertEqual(update_id, 1234)

    def test_incorrect(self):
        message_text = '''{"k":"v","update_id":1234,
"message":{"message_id":1,"from":{"id":12345,"is_bot":false,"first_name":"Name","username":"user","language_code":"en-US"},"chat":{"id":1234,"first_name":"Name","username":"user","type":"private"},"date":0,"text":"test"}}'''

        with self.assertRaises(tg2sock.parser.DecoderError) as de:
            get_update_id(message_text)

        self.assertEqual(str(de.exception), "Expected update_id as first key, got 'k'")


class JSONObjectAsStrTest(unittest.TestCase):

    def setUp(self):
        self._parse = tg2sock.parser.JSONObject_asStr

    def _verify_same(self, some_json):
        parsed, offt = self._parse((some_json, 1))
        self.assertEqual(parsed, some_json)
        self.assertEqual(offt, len(some_json))

    def test_empty_object(self):
        self._verify_same('{}')

    def test_simple_object(self):
        self._verify_same('{"key":"value"}')

    def test_nested_object(self):
        self._verify_same('{"key":{}}')

    def test_not_actual_object(self):
        self._verify_same('{"key":"{"}')

    def test_escaped_quote(self):
        self._verify_same('{"key":"\\""}')

    def test_escaped_backslash(self):
        self._verify_same('{"key":"\\\\"}')

    def test_newlines_outside_strings_should_be_converted_to_spaces(self):
        some_json = '''{"key":
"value"}'''
        parsed, offt = self._parse((some_json, 1))
        self.assertEqual(parsed, '{"key": "value"}')
        self.assertEqual(offt, len(some_json))
