#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import hashlib
import socket
import thread
import json
import time

#  Python server for websocket, http, JS and html based multi user chat
#  Creator: Yiftah Schlesinger, 11th grade cyber class, Handesaim Highschool Herzliya 2020
#  Run this and follow this link to go to a client: http://localhost

CHAT_PORT = 52435  # websocket chat port

user_sockets = {}  # dictionary of the websocket client sockets. Key: username, Value: socket

server = None  # type: socket.socket

running = True


def get_crnt_time():
    """
    get current time in milliseconds as a string
    :return: string current time
    """
    return str(int(round(time.time() * 1000)))


def find_accept(ws_key):
    """
    Generate websocket response key from websocket request key.
    :param ws_key: Websocket request key
    :return: Websocket response key
    """
    ws_key = ws_key.replace(' ', '')
    ws_key += '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    sha_hash = hashlib.sha1(ws_key.encode()).hexdigest().decode('hex')
    return base64.b64encode(sha_hash)


def read_msg(client):
    """
    read a msg from the client in webserver protocol
    :param client: socket of the client
    :type client: socket.socket
    :return: client msg as string
    """
    data = bytearray(client.recv(1024))  # read bytes from the client
    fin = False  # if fin is on, this is the last packet
    result = ""
    while not fin:
        if len(data) == 0:
            data = bytearray(client.recv(1024))
        opcode = data[0] & 0b00001111
        # the four lower bits of the first byte are the opcode
        # opcode 8 = close connection
        # opcode 9 = ping, expecting to receive a "pong" message from the server with the same content
        # opcode 10 = pong, response to ping request from the server
        # other opcodes = message
        if opcode == 8:
            return '{"action": "close"}'
        if opcode == 9:
            result = '{"action": "ping", "data": "'
        if opcode == 10:
            result = '{"action": "pong", "data": "'
        if len(data) < 20:
            data += bytearray(client.recv(1024))
        fin = (data[0] & 0x80) != 0  # fin is the first bit in the data
        should_mask = (data[1] & 0x80) != 0  # the upper bit in the second byte indicates whether or not the message
        # is encrypted in xor mask
        assert should_mask, "Messages from client must be masked!"  # if a message from the client isn't masked,
        # the connection must be closed
        length = data[1] & 0b01111111  # message length
        pointer = 2  # points to the next byte to read
        if length == 126:  # if the length is less than 126, that's the length
            # if the length is 126, the length is actually the next 2 bytes
            length = (data[2] << 8) | data[3]
            pointer = 4
        elif length == 127:
            # if the length is 127, the length is actually the next 8 bytes.
            length = data[2] << 56
            length += data[3] << 48
            length += data[4] << 40
            length += data[5] << 32
            length += data[6] << 24
            length += data[7] << 16
            length += data[8] << 8
            length += data[9]
            pointer = 10
        mask = data[pointer:pointer + 4]  # messages are encrypted with xor mask
        #  there are 4 random bytes sent before the message
        #  and every 4 bytes in the message should be xor masked with these bytes
        pointer += 4
        for i in xrange(length):  # read every byte from the data, mask it and add to result
            if pointer == len(data):  # if the data array is over and the message isn't, read more bytes
                data = bytearray(client.recv(1024))
                pointer = 0
            result += chr(data[pointer] ^ mask[i % 4])
            pointer += 1
        data = data[pointer:]  # delete the data that was already added to the result
        if opcode in (9, 10):  # see if opcode == 9, if opcode == 10 above
            result += '"}'
    return result


def send_msg(client, msg, first_byte=0b10000001):
    """
    Send a message to the client.
    :param client: client socket
    :type client: socket.socket
    :param msg: message as a string
    :param first_byte: the first byte of the data (fin and opcode)
    :return: None
    """
    length = len(msg)
    data = [first_byte]
    if length < 126:  # set message length according to websocket rules
        data.append(length)
    elif length < (1 << 16):
        data.append(126)
        data.append(length >> 8)
        data.append(length & 0x00ff)
    elif length < (1 << 31):
        data.append(127)
        data.append(length >> 24)
        data.append((length >> 16) & 0x000000ff)
        data.append((length >> 8) & 0x000000ff)
        data.append(length & 0x000000ff)
    client.send(bytearray(data))
    client.send(msg)


def send_to_all(sender, msg, img=False):
    """
    Send a message to all the users
    :param sender: The username of the user that sent the message. admin if it's an auto message
    :param msg: Message or image name
    :param img: if true, this messages is a link to an image. It sets the action to send_img,
                the message content is the link
    :return: nothing
    """
    for user in user_sockets.keys():
        try:
            send_msg(user_sockets[user], '{"action": "' + ('send_img' if img else 'new_msg') + '",' +
                     '"sender": "' + sender + '",' +
                     '"content": "' + msg + '"}')
        except IOError:  # in case the client disconnected or other connection error
            print 'error sending message to user ' + user
            print 'closing connection'
            user_sockets[user].close()
            del user_sockets[user]


def listen_to_user(client, username):
    """
    This function runs in parallel for every user that connects, using threads.
    It listens to client messages and handles them.
    :param client: client socket of the client
    :type client: socket.socket
    :param username: The username of the client
    :return: nothing
    """
    print 'listening to user ' + username
    connected = True  # this variable keeps the loop running as long as it is set as True.
    while connected:
        msg = json.loads(read_msg(client))  # read a message from the client and convert it from
        # JSON to dictionary
        print 'received msg from', username
        print msg
        if 'action' not in msg.keys():
            continue
        if msg['action'] == 'send_msg' and 'content' in msg.keys():  # the client sent a message
            msg_content = msg['content']
            if msg_content[0:3] == '%40':  # The client tagged another user with @ and then username
                # if the user exists, the message will be sent to him only
                to = msg_content.split('%20')[0][3:]  # user to send the message to
                if to in user_sockets.keys():  # if the user exists send him the message
                    send_msg(user_sockets[to],
                             '{"action": "new_msg", "sender": "' + username + '", "content": "' + msg_content + '"}')
                    if to != username:  # send it to the sender to notify that the message is sent
                        send_msg(client,
                                 '{"action": "new_msg", "sender": "' + username + '", "content": "' + msg_content + '"}')
                else:  # if the user does not exist, send an error message to the user
                    send_msg(client,
                             '{"action": "new_msg", "sender": "admin", "content": "Error: user @' + to + ' does not '
                                                                                                         'exist"}')
            else:  # if no user is tagged, send the message to all users
                send_to_all(username, msg_content)
        if msg['action'] == 'send_img' and 'type' in msg.keys():  # when the user sends a message, the client will first
            # send a message with the action 'send_img', and then send the image
            img = read_msg(client)  # read the contents of the image
            file_type = msg['type'].lower()  # get the file type
            if file_type not in ['jpg', 'jpeg', 'png', 'gif']:  # check that the file is an image
                continue
            fname = get_crnt_time() + '.' + file_type  # save the file with the current time as file name
            with open('imgs/' + fname, 'wb') as wfile:
                wfile.write(img)  # save image on server
            send_to_all(username, fname, True)  # send a link to the image, will be accessed using http
        if msg['action'] == 'close':  # if the client sends a closing websocket message,
            # close the connection. It happens when the client closes the tab
            del user_sockets[username]
            send_to_all('admin', username + ' has left the chat')
            connected = False
            send_msg(client, 'closing connection', 0b10001000)  # send close message with close opcode
        if msg['action'] == 'ping':  # a ping is a websocket message that checks if the server is still on
            send_msg(client, msg['data'], 0b10001010)  # send 'pong' message


def wait_for_login(client):
    """
    Wait for a client that just connected to websocket to login with a username
    :param client: client socket
    :type client: socket.socket
    :return: nothing
    """
    print 'waiting for login'
    success = False
    while not success:
        try:
            client_json = json.loads(read_msg(client))  # get the message as json
        except AssertionError:
            client.close()
            return
        if 'action' in client_json.keys() and client_json['action'] == 'login' \
                and 'username' in client_json.keys():  # if request is valid
            username = client_json['username']
            if username == 'admin' or ' ' in username or username in user_sockets.keys():  # check if the username is taken
                send_msg(client, "{\"action\": \"login\", \"result\": \"failure\", \"reason\": \"name_taken\"}")
            else:
                send_msg(client, "{\"action\": \"login\", \"result\": \"success\"}")
                print 'logged in'
                success = True
                user_sockets[username] = client
                send_to_all('admin', username + ' connected')  # send a message to all users
                # to notify that the user connected
                listen_to_user(client, username)  # listen to user message
        else:
            #  bad request
            send_msg(client, "{\"action\": \"login\", \"result\": \"failure\", \"reason\": \"bad request\"}")


def handle_client(client, addr):
    """
    Handle a client that just connected to the server.
    The connection should begin in HTTP protocol, with parameters Connection: Upgrade
    and Upgrade: websocket, and a websocket key.
    :param client: Socket object of the client
    :type client: socket.socket
    :param addr: address of the client. tuple (ip, port)
    :type addr: tuple
    :return: None
    """
    print 'received new connection. address:', addr
    try:
        data = client.recv(1024)
        lines = data.split('\r\n')  # Split the http request to lines
        res_code = '400 Bad Request'
        for i in [0]:  # the loop runs once in order to allow breaking at any point
            if len(lines) < 4:  # if the request is too short, it is a bad request
                break
            try:
                method, action = lines[0].split(' ')[:2]
            except:
                break
            if method != 'GET':
                break
            if action != '/connect':
                res_code = '404 Not Found'
                break
            params = {}
            for line in lines[1:]:
                if ': ' in line:
                    key = line.split(': ')[0]
                    params[key] = line[len(key) + 2:]
            if 'Connection' not in params.keys() or \
                    params['Connection'] != 'Upgrade' or \
                    'Upgrade' not in params.keys() or \
                    params['Upgrade'] != 'websocket' or \
                    'Sec-WebSocket-Key' not in params.keys():
                break
            key = params['Sec-WebSocket-Key']  # Get websocket request key from params
            accept = find_accept(key)  # generate websocket response key
            client.send('HTTP/1.1 101 Switching Protocols\r\n'
                        'Connection: Upgrade\r\n'
                        'Upgrade: websocket\r\n'
                        'Sec-Websocket-Accept: ' + accept + '\r\n\r\n')  # send response
            wait_for_login(client)  # wait for login with username
            return
        client.send('HTTP/1.1 ' + res_code + '\r\n\r\n')  # if there was an error, send it
    except IOError as err:
        print 'IOError. closing connection'
        print err
        client.close()


def start_websocket_server():
    global server, running
    server = socket.socket()
    server.bind(('0.0.0.0', CHAT_PORT))
    server.listen(5)
    while running:
        client, addr = server.accept()
        thread.start_new_thread(handle_client, (client, addr))


def close_websocket_server():
    global server, running
    running = False
    server.close()
