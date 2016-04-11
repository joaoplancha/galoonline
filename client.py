import socket
import sys
import select

SERVER_PORT = 12000
SERVER_IP = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# o select quer ficar a espera de ler o socket e ler do stdin (consola)
inputs = [sock, sys.stdin]

# status - unregistered = 0; registered and free = 1; registered and busy = 2;
status = 0
name = " "
opponent = " "


def update_status(new):
    global status
    status = new


def update_opponent(client):
    global opponent
    opponent = client


def ack_server():
    # send the ack to server
    sock.sendto("OK", (SERVER_IP, SERVER_PORT))


def ack_client(m):
    arg2 = m.split['$'][1].split[';'][0]
    arg1 = m.split['$'][1].split[';'][1]
    ack_msg = "OK$" + arg1 + ";" + arg2
    # send the ack to client (through server relay)
    sock.sendto(ack_msg, (SERVER_IP, SERVER_PORT))


def register(m):
    msg_to_server = m[0] + "$" + m[1]
    result = outbound(msg_to_server)

    # check if ACK was received by outbound()
    if result == "OK":
        update_status(1)
        global name
        name = m[1]
        print("Registered with the name: " + name)
    else:
        print(result)


def unregister(m):
    msg_to_server = m[0]
    result = outbound(msg_to_server)

    # check if ACK was received by outbound()
    if result == "OK":
        update_status(0)
        global name
        name = " "
    else:
        print(result)


def list_request():

    trials = 0
    max_trials = 9
    sock.settimeout(1.0)
    msg_reply = " "

    while trials < max_trials:
        try:
            sock.sendto("list", (SERVER_IP, SERVER_PORT))
            (msg_reply, address) = sock.recvfrom(1024)
            ack_server()
            break;
        except socket.timeout:
            trials += 1

    sock.settimeout(None)

    if trials == max_trials:
        print("ERROR: unable to reach server")
    else:
        print(msg_reply)


def invite(m):

    invite_msg = m[0] + "$" + name + ";" + m[1]
    result = outbound(invite_msg)

    if result == "OK":
        result = inbound(20.0)
        if result.split('$')[0] == "inviteR" and result.split('$')[1].split(';')[0] == "Y":
            print("Invitation accepted")
            update_status(2)
            update_opponent(m[1])
            return
        elif result.split('$')[0] == "inviteR" and result.split('$')[1].split(';')[0] == "N":
            print("Invitation not accepted")
            return
        else:
            print(result)
    else:
        print(result)


def invite_reply(m):

    reply_msg_y = "inviteR$Y;" + name + ";" + opponent
    reply_msg_n = "inviteR$N;" + name + ";" + opponent

    invite_msg = m[1].split(';')
    print(invite_msg[0] + " is inviting you to play")
    print("Do you accept the invitation? (Y/N)")
    choice = sys.stdin.readline()
    if choice == "Y":
        result = outbound(reply_msg_y)
        if result == "OK":
            print(status)
            update_status(2)
            print(status)
            print(opponent)
            update_opponent(invite_msg[0])
            print(opponent)
            play_wait()
        else:
            print(result)
            return
    elif choice == "N":
        outbound(reply_msg_n)
        return


def play(m):
    msg_to_server = m[0] + "$" + m[1] + ";" + name + ";" + opponent
    # falta aqui a logica de jogo
    result = outbound(msg_to_server)

    if result == "OK":
        result = play_wait()
        if result == "quit":
            # need to update server as well... after that, we can reduce the timeout
            update_status(1)
            return
    else:
        print(result)
        # need to update server as well... after that, we can reduce the timeout
        update_status(1)
        print("quitting game...")
        return


def play_wait():
    print("entered wait")

    ok_msg = "OK$" + name + ";" + opponent

    # wait for opponent to play
    print("Waiting for the other player to make a move...")
    while True:
        result = inbound(1000.0)
        if result.split('$')[0] == "play":
            # falta aqui a logica de jogo
            sock.sendto(ok_msg, (SERVER_IP, SERVER_PORT))
            return
        elif result.split('$')[0] == "fim":
            print("Game ended: " + result.split('$')[1].split(';')[0])
            print("quitting game...")
            update_status(1)
            return "quit"
        else:
            print("result")
            print("quitting game...")
            return "quit"


def inbound(time):
    #sock.settimeout(time)
    try:
        (msg_reply, address) = sock.recvfrom(1024)
        sock.settimeout(None)
    except socket.timeout:
        sock.settimeout(None)
        return "ERROR: No reply received from the client"

    return msg_reply


def outbound(msg_to_server):
    trials = 0
    max_trials = 9
    # 1s timeout
    # sock.settimeout(1.0)

    msg_reply = " "
    # send message to server
    # if no reply is received after 1s, the message will be sent again
    # this procedure is going to be repeated up to 9 times, before warning the user
    while trials < max_trials:
        try:
            sock.sendto(msg_to_server, (SERVER_IP, SERVER_PORT))
            (msg_reply, address) = sock.recvfrom(1024)
            break;
        except socket.timeout:
            trials += 1
    sock.settimeout(None)

    if trials == max_trials:
        return "ERROR: unable to reach server"
    elif msg_reply == "OK":
        return "OK"
    elif msg_reply.split('$')[0] == "NOK":
        return msg_reply.split('$')[1]


while True:
    print("Input message to server below.")
    ins, outs, exs = select.select(inputs, [], [])
    # select devolve para a lista ins quem esta a espera de ler
    for i in ins:
        # i == sys.stdin - alguem escreveu na consola, vamos ler e enviar
        if i == sys.stdin:
            # sys.stdin.readline() le da consola
            msg_temp = sys.stdin.readline()
            msg = msg_temp.split(' ')

            if msg[0] == "register":
                if status != 0:
                    print("ERROR: You're already registered with the server")
                else:
                    register(msg)
            elif msg[0] == "unregister\n":
                if status == 0:
                    print("ERROR: You're not registered with the server")
                elif status == 2:
                    print("ERROR: You must finish your game first")
                else:
                    unregister(msg)
            elif msg[0] == "list\n":
                print("requesting list...")
                list_request()
            elif msg[0] == "invite":
                if status == 0:
                    print("ERROR: You're not registered with the server")
                elif status == 2:
                    print("ERROR: You must finish your game first")
                else:
                    invite(msg)
            elif msg[0] == "play":
                if opponent == " ":
                    print("You cannot play without choosing an opponent")
                elif status == 0:
                    print("ERROR: You're not registered with the server")
                elif status == 2:
                    print("ERROR: You must finish your game first")
                else:
                    play(msg)

            # envia mensagem da consola para o servidor
        # i == sock - o servidor enviou uma mensagem para o socket
        elif i == sock:
            (msg_temp, addr) = sock.recvfrom(1024)
            msg = msg_temp.split('$')
            if msg[0] == "invite":
                invite_reply(msg)
            else:
                "don't know what to do"


