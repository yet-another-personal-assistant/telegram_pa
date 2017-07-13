#!/bin/sh

message="$@"
thisfile=$(readlink -f "$0")

if [ ! -S /tmp/pa_socket ] ; then
    stop_cmd=stop
    (cd $(dirname "$thisfile");
     . .env/bin/activate;
     ./pa.py --no-greet --no-goodbye &)
    while [ ! -S /tmp/pa_socket ] ; do
	sleep 1
    done
fi

exec socat STDIO UNIX-CONNECT:/tmp/pa_socket <<EOF
message:$message
$stop_cmd
EOF
