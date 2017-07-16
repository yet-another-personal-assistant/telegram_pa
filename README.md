A simple interface between UNIX socket and telegram chat.

[![Build Status](https://travis-ci.org/aragaer/telegram_pa.svg?branch=master)](https://travis-ci.org/aragaer/telegram_pa) [![codecov](https://codecov.io/gh/aragaer/telegram_pa/branch/master/graph/badge.svg)](https://codecov.io/gh/aragaer/telegram_pa)

Use the following command to send commands to her from console:

socat STDIO UNIX-CONNECT:/tmp/pa_socket

Stop the process with either SIGINT, SIGTERM or "stop" command sent to the socket.