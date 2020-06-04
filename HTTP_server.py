#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import thread
import os

from ws_chat import CHAT_PORT

HTTP_PORT = 80


# dictionary. keys are file names, values are tuples of (internal server url, content type)
http_files = {"/": ("public_html/index.html", "text/html"), "/index.html": ("public_html/index.html", "text/html"),
              "/ws_functions.js": ("public_html/ws_functions.js", "text/javascript"),
              "/image.webp": ("public_html/image.webp", "image/webp"), "/style.css": ("public_html/style.css", "text/css")}

img_types = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif"}

http_server = None  # type: socket.socket

running = True


def handle_http_client(client, addr):
    """
    Handle an http request (not for the chat server, the HTTP server to access the webpage)
    :type client: socket.socket
    :param client: HTTP client socket
    :param addr: address as a tuple (ip, port)
    :return: nothing
    """
    print 'received new connection from', addr
    try:
        data = client.recv(1024).split('\r\n')
        title = data[0].split(' ')  # split the HTTP request to lines
        if title[0] != 'GET':  # The HTTP server only deals with GET requests
            client.send('HTTP/1.1 400 Bad Request\r\n\r\n')
            client.close()
            return
        if '?' in title[1] and title[1].split('?')[0] == '/image':  # Getting images sent in the chat
            params = title[1].split('?')  # The image link is in the url params
            if len(params) == 2:
                params = params[1]
                if len(params.split('=')) == 2 and params.split('=')[0] == 'imgId':
                    imgId = params.split('=')[1]
                    path = 'imgs/' + imgId
                    if os.path.exists(path):  # if the image exists, send it
                        type = 'image/' + img_types[path.split('.')[-1]]
                        with open(path, 'rb') as rfile:
                            content = rfile.read()
                            client.send('HTTP/1.1 200 OK\r\nContent-Type: ' + type + '\r\n' +
                                        'Content-Length: ' + str(len(content)) + '\r\n\r\n')
                            client.send(content)
                            client.close()
                        return
                    client.send('HTTP/1.1 404 File Not Found\r\n\r\n')
                    client.close()
                    return
            client.send('HTTP/1.1 400 Bad Request\r\n\r\n')
            client.close()
            return
        if title[1] not in http_files.keys():  # handling 404 errors
            client.send('HTTP/1.1 404 File Not Found\r\n\r\n')
            client.close()
            return
        (file_url, content_type) = http_files[title[1]]  # get the internal url and the content type
        with open(file_url, 'rb') as rfile:
            content = rfile.read()  # get file contents
            if title[1] == '/ws_functions.js':
                # set websocket port in client's call to the websocket port
                # see public_html/ws_functions.js function try_login
                content = content.replace('[[[PORT_PLACEHOLDER]]]', str(CHAT_PORT))
            client.send('HTTP/1.1 200 OK\r\nContent-Type: ' + content_type + '\r\nContent-Length: ' +
                        str(len(content)) + '\r\n\r\n')
            client.send(content)
        client.close()
    except:
        return


def start_http_server():
    """
    Start the http server, and run it in the background using a thread
    :return:
    """
    global http_server, running
    http_server = socket.socket()
    http_server.bind(('0.0.0.0', HTTP_PORT))
    http_server.listen(5)
    while running:  # handle client connections
        client, addr = http_server.accept()
        thread.start_new_thread(handle_http_client, (client, addr))


def close_http_server():
    global http_server, running
    running = False
    http_server.close()
