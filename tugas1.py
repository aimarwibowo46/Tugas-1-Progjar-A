#!/usr/bin/env python3
# Foundations of Python Network Programming, Third Edition
# https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter03/tcp_sixteen.py
# Simple TCP client and server that send and receive 16 octets

import argparse
import socket
import sys
import glob
import os


def makeDirIfNotExist(path):
    isExist = os.path.exists(path)

    if not isExist:
        os.makedirs(path)


def encode(rawMsg):
    msg = bytes(rawMsg, 'utf-8')
    len_msg = b'%03d' % (len(msg))
    msg = len_msg + msg
    return msg


def recvall(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError('was expecting %d bytes but only received'
                           ' %d bytes before the socket closed'
                           % (length, len(data)))
        data += more
    return data


def receiveReply(sock):
    len_msg = recvall(sock, 3)
    message = recvall(sock, int(len_msg))
    # print('INFO: reply length is ' + repr(len_msg))

    return message.decode('utf-8')


def server(interface, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((interface, port))
    sock.listen(1)
    print('Listening at', sock.getsockname())

    makeDirIfNotExist('server_files')

    while True:
        print('Waiting to accept a new connection')
        sc, sockname = sock.accept()
        print('We have accepted a connection from', sockname)
        print('  Socket name:', sc.getsockname())
        print('  Socket peer:', sc.getpeername())

        while True:
            len_msg = recvall(sc, 3)
            message = recvall(sc, int(len_msg))
            print('  Message len:', repr(len_msg))
            print('  Incoming message:', repr(message))

            commands = (message.decode('utf-8')).split()

            if commands[0] == "ls":
                if len(commands) == 1:
                    dire = glob.glob('*')
                else:
                    dire = glob.glob(commands[1])

                repl = ''

                for i in dire:
                    repl += i + '\n'

                sc.sendall(encode(repl))
            elif commands[0] == "get":
                if os.path.exists(commands[1]):
                    size = os.path.getsize(commands[1]) / 1024

                    onlyFileName = (commands[1].split('/'))[-1]
                    message = ("file found, file name '" +
                               onlyFileName + "', file size '" + str(size) + "'")
                    sc.sendall(encode(message))

                    f = open(commands[1], 'rb')
                    l = f.read(1024)
                    while (l):
                        sc.send(l)
                        if len(l) < 1024:
                            break
                        l = f.read(1024)

                    f.close()

                    continue

                sc.sendall(encode("ERROR: file not found"))

            elif commands[0] == "ping":
                commands.pop(0)

                sc.sendall(encode(" ".join(commands)))

            elif commands[0] == "send":
                sc.sendall(encode('INFO: server is ready to receive file'))
                repl = receiveReply(sc)

                if repl == 'error':
                    continue
                
                f = open('server_files/' + commands[2], 'wb')
                l = sc.recv(1024)
                while (l):
                    f.write(l)
                    if len(l) < 1024:
                        break
                    l = sc.recv(1024)
                f.close()

            elif commands[0] == "quit":
                sc.sendall(b'Farewell, client')
                sc.close()
                print('  Reply sent, socket closed')
                break


def client(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print('Client has been assigned socket name', sock.getsockname())

    makeDirIfNotExist('client_files')

    while True:
        command = input("> ")
        commands = command.split()

        msg = bytes(command, 'utf-8')
        len_msg = b'%03d' % (len(msg))
        msg = len_msg + msg

        if commands[0] == "ls":
            sock.sendall(msg)

            print(receiveReply(sock))
        elif commands[0] == "get":
            if len(commands) != 3:
                print('ERROR: missing args for command \'get\'')
                continue

            print('INFO: attempting to get file from \'' + commands[1] + '\'')
            print('INFO: file will be saved as \'' + commands[2] + '\'')
            sock.sendall(msg)

            repls = receiveReply(sock).split(', ')

            if len(repls) == 1:
                print(repls[0])
                continue

            for i in repls:
                print('INFO: ' + i)

            f = open('client_files/' + commands[2], 'wb')
            l = sock.recv(1024)
            while (l):
                f.write(l)
                if len(l) < 1024:
                    break
                l = sock.recv(1024)
            f.close()

        elif commands[0] == "ping":
            sock.sendall(msg)

            print(receiveReply(sock))

        elif commands[0] == "send":
            if len(commands) != 3:
                print('ERROR: missing args for command \'send\'')
                continue

            sock.sendall(msg)
            print(receiveReply(sock))

            if not os.path.exists(commands[1]):
                print('ERROR: unable to find specified file \'' + commands[1] + '\'')
                sock.sendall(encode('error'))
                continue
            
            onlyFileName = (commands[1].split('/'))[-1]
            size = os.path.getsize(commands[1]) / 1024

            print('INFO: attempting to send file \'' + onlyFileName + '\'')
            print('INFO: file size to be sent is \'' + str(size) + '\'')
            print('INFO: server will save file as \'' + commands[2] + '\'')
            sock.sendall(encode('success'))

            f = open(commands[1], 'rb')
            l = f.read(1024)
            while (l):
                sock.send(l)
                if len(l) < 1024:
                    break
                l = f.read(1024)

            f.close()

        elif commands[0] == "quit":
            print('INFO: closing connection to server')
            sock.sendall(msg)
            recvall(sock, 16)
            sock.close()
            break
        else:
            print('ERROR: unexpected command \'' + commands[0] + '\'')


if __name__ == '__main__':
    choices = {'client': client, 'server': server}
    parser = argparse.ArgumentParser(description='Send and receive over TCP')
    parser.add_argument('role', choices=choices, help='which role to play')
    parser.add_argument('host', help='interface the server listens at;'
                        ' host the client sends to')
    parser.add_argument('-p', metavar='PORT', type=int, default=1060,
                        help='TCP port (default 1060)')
    args = parser.parse_args()
    function = choices[args.role]
    function(args.host, args.p)