#!/usr/bin/env python3
from nltk.data import find
from nltk.tag.perceptron import PerceptronTagger
from nltk.tokenize import word_tokenize

import sys


_TAGGER_RU="averaged_perceptron_tagger_ru"
_PICKLE="taggers/{0}/{0}.pickle".format(_TAGGER_RU)


if __name__ == '__main__':
    tagger = PerceptronTagger(load=False)
    tagger.load("file:"+str(find(_PICKLE)))
    sys.stderr.write("started\n")
    sys.stdout.write("register backend\n")
    sys.stdout.write("message:nltk\n")
    sys.stderr.write("reading now\n")
    for line in sys.stdin:
        if not line:
            break
        if not line.startswith('message:'):
            continue
        phrase = line[8:].strip()
        sys.stdout.write("message:{}\n".format(tagger.tag(word_tokenize(phrase))))
