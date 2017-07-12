A simple interface between UNIX socket and telegram chat.

Use the following command to send commands to her from console:

socat STDIO UNIX-CONNECT:/tmp/pa_socket

Stop the process with either SIGINT, SIGTERM or "stop" command sent to the socket.