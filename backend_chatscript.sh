#!/bin/bash

cat <<'EOF' > /tmp/my_script
#!/bin/bash
send_message() {
    /bin/echo -ne "aragaer\0\0$1\0" | socat STDIO TCP:localhost:1024
}

echo 'register backend'
echo "message: $(send_message)"
while read line ; do
    message=${line/message:/}
    echo $message >&2
    response=$(send_message "$message")
    echo message: $response
    echo $response >&2
done
EOF
chmod +x /tmp/my_script

socat EXEC:/tmp/my_script UNIX-CONNECT:/tmp/pa_socket
