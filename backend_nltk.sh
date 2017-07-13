#!/bin/sh

thisfile=$(readlink -f "$0")
(cd $(dirname "$thisfile")
 export NLTK_DATA=./nltk_data
 . .env/bin/activate
 socat UNIX-CONNECT:/tmp/pa_socket EXEC:./backend_nltk.py,pty)
