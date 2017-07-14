#!/bin/sh

thisfile=$(readlink -f "$0")
socket=$1
test $socket || socket=/tmp/pa_socket
(cd $(dirname "$thisfile")
 export NLTK_DATA=./nltk_data
 . .env/bin/activate
 socat UNIX-CONNECT:$socket EXEC:./backend_nltk.py,pty)
