#!/bin/sh +x

message="$@"
thisdir=$(readlink -f $(dirname $0))

if [ ! -S /tmp/pa_socket ] ; then
    stop_cmd=stop
    . "$thisdir"/.env/bin/activate
    "$thisdir"/pa.py --no-greet --no-goodbye &
    while [ ! -S /tmp/pa_socket ] ; do
	sleep 1
    done
fi

socat STDIO UNIX-CONNECT:/tmp/pa_socket <<EOF
message:$message
$stop_cmd
EOF
