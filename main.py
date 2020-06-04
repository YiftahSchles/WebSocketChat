#!/usr/bin/env python
# -*- coding: utf-8 -*-
from HTTP_server import start_http_server, HTTP_PORT, close_http_server
from ws_chat import start_websocket_server, CHAT_PORT, close_websocket_server
import thread
import socket

running = True


def main():
    """
    start the program
    :return:
    """
    global running
    thread.start_new_thread(start_http_server, ())
    print 'Server started. Link to client:'
    print 'http://' + str(socket.gethostbyname(socket.gethostname())) + '' if HTTP_PORT == 80 else (
            ':' + str(HTTP_PORT))
    thread.start_new_thread(start_websocket_server, ())
    while raw_input() != 'exit':
        pass
    close_http_server()
    close_websocket_server()
    exit(0)


if __name__ == "__main__":
    main()
