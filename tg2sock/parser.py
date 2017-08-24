import json

from io import StringIO
from json.decoder import JSONObject
from json.scanner import py_make_scanner


def JSONObject_asStr(s_and_end, *args, **kwargs):
    s, pos = s_and_end
    output = StringIO()
    output.write('{')
    count = 1
    in_string = False
    while count:
        if s[pos] == '\\':
            output.write(s[pos:pos+2])
            pos += 2
            continue
        if s[pos] == '\n':
            output.write(' ')
            pos += 1
            continue
        if s[pos] == '"':
            in_string = not in_string
        elif not in_string:
            if s[pos] == '}':
                count -= 1
            elif s[pos] == '{':
                count += 1
        output.write(s[pos])
        pos += 1
    return output.getvalue(), pos


_decoder = json.JSONDecoder()
_decoder.parse_object = JSONObject_asStr
_decoder.scan_once = py_make_scanner(_decoder)


def parse(text):
    return JSONObject((text, 1), True, _decoder.scan_once, None, None)[0]


def get_update_id(s):
    key, offt = _decoder.raw_decode(s, 1)
    if key != "update_id":
        raise DecoderError("Expected update_id as first key, got '{}'".format(key))
    return _decoder.raw_decode(s, s.find(":", offt) + 1)[0]


class DecoderError(Exception):
    pass
