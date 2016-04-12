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
board = []
piece = " "


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
    arg2 = m.split('$')[1].split(';')[0]
    arg1 = m.split('$')[1].split(';')[1]
    ack_msg = "OK$" + arg1 + ";" + arg2
    print("ack: "+ ack_msg)
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
    msg_reply = ""

    while trials < max_trials:
        try:
            sock.sendto("list", (SERVER_IP, SERVER_PORT))
            (msg_reply, address) = sock.recvfrom(1024)
            ack_server()
            break
        except socket.timeout:
            trials += 1

    sock.settimeout(None)

    if trials == max_trials:
        print("ERROR: unable to reach server")
    else:
        print("--------- PLAYER LIST ---------")
        print("-------------------------------")
        print("Name \t\t\tStatus")
        print("-------------------------------")
        msg_reply = msg_reply.split('$')[1]
        l = msg_reply.split(', ')
        j = 0
        while j < len(l):
            namel = str(l[j].split(":")[0]).replace('\'', "")
            statusl = str(l[j].split(":")[1]).replace('\'', "")
            # namel = str(l[j].split(":")[0])[1:len(str(l[j].split(":")[0]))]
            # statusl = str(l[j].split(":")[1])[0:len(str(l[j].split(":")[0]))-1]
            print(namel + "\t\t\t" + statusl)
            j += 1
        print("-------------------------------")


def invite(m):
    # invite message formation to send through server to the client we want to invite
    invite_msg = m[0] + "$" + name + ";" + m[1]
    # send the message to client through server
    # it's the server responsibility to interpret and relay as appropriate
    result = outbound(invite_msg)

    if result == "OK":
        print("invitation received by other client. waiting for reply")
        (reply, address) = sock.recvfrom(1024)
        # result = inbound(60.0)
        if reply.split('$')[0] == "inviteR" and reply.split('$')[1].split(';')[0] == "Y":
            ack_client("OK$" + m[1] + ";" + name)
            print("OK$" + name + ";" + m[1])
            print("Invitation accepted")
            update_status(2)
            update_opponent(m[1])
            sock.sendto("busy", (SERVER_IP, SERVER_PORT))
            global piece
            piece = "X"
            ttt_start_game()
            ttt_play()
        elif reply.split('$')[0] == "inviteR" and reply.split('$')[1].split(';')[0] == "N":
            ack_client("OK$" + m[1] + ";" + name)
            print("Invitation not accepted")
            return
        else:
            print(result)
    else:
        print(result)


def invite_reply(m):

    invite_msg = m[1].split(';')

    reply_msg_y = "inviteR$Y;" + invite_msg[1] + ";" + invite_msg[0]
    reply_msg_n = "inviteR$N;" + invite_msg[1] + ";" + invite_msg[0]

    print(invite_msg[0] + " is inviting you to play")
    print("Do you accept the invitation? (Y/N)")

    choice = sys.stdin.readline()
    if choice == "Y\n":
        result = outbound(reply_msg_y)
        if result == "OK":
            print(status)
            update_status(2)
            print(status)
            print(opponent)
            update_opponent(invite_msg[0])
            print(opponent)
            sock.sendto("busy", (SERVER_IP, SERVER_PORT))
            global piece
            piece = "O"
            ttt_start_game()
            play_wait()
        else:
            print(result)
            return
    elif choice == "N\n":
        outbound(reply_msg_n)
        return
    return


def ttt_start_game():
    j = 0
    while j <= 8:
        board.append(j)
        j += 1


def ttt_play():
    print
    print(" " + str(board[0]) + " | " + str(board[1]) + " | " + str(board[2]))
    print(" --- --- ---")
    print(" " + str(board[3]) + " | " + str(board[4]) + " | " + str(board[5]))
    print(" --- --- ---")
    print(" " + str(board[6]) + " | " + str(board[7]) + " | " + str(board[8]))
    print
    print("Make your move (0-8)")
    move = sys.stdin.readline()
    place = int(move)

    play(place)
    return


def play(place):

    msg_to_server = "play$" + name + ";" + opponent + ";" + str(place)
    result = outbound(msg_to_server)

    if result == "OK":
        result = play_wait()
        if result == "quit":
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            update_status(1)
            return
    else:
        print(result)
        ttt_play()


def play_wait():
    print("entered wait")

    ok_msg = "OK$" + name + ";" + opponent
    nok_msg = "NOK$" + name + ";" + opponent + "Invalid move"
    end_msg_v = "fim$" + name + ";" + opponent + "Victory"
    end_msg_d = "fim$" + name + ";" + opponent + "Draw"

    # wait for opponent to play
    print("Waiting for the other player to make a move...")
    while True:
        # result = inbound(1000.0)
        (result, address) = sock.recvfrom(1024)
        print("jogada recebida: " + result)
        place = int(result.split('$')[1].split(';')[2])
        if result.split('$')[0] == "play":
            if board[place] == "X" or board[place] == "Y":
                sock.sendto(nok_msg, (SERVER_IP, SERVER_PORT))
                # continue to wait
                continue
            else:
                board[place] = piece
                sock.sendto(ok_msg, (SERVER_IP, SERVER_PORT))
                game_state = check_if_win()
                if game_state == "win":
                    outbound(end_msg_v)
                    return
                elif game_state == "draw":
                    outbound(end_msg_d)
                    continue
                elif game_state == "ongoing":
                    ttt_play()
        elif result.split('$')[0] == "fim":
            print("Game ended: " + result.split('$')[1].split(';')[0])
            print("quitting game...")
            update_status(1)
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            return "quit"
        else:
            print("result")
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            print("quitting game...")
            return "quit"


def check_if_win():
    # lines
    if board[0] == board[1] == board[2]:
        return "win"
    elif board[3] == board[4] == board[5]:
        return "win"
    elif board[6] == board[7] == board[8]:
        return "win"
    # columns
    elif board[0] == board[3] == board[6]:
        return "win"
    elif board[1] == board[4] == board[7]:
        return "win"
    elif board[2] == board[5] == board[8]:
        return "win"
    # diagonals
    elif board[0] == board[4] == board[8]:
        return "win"
    elif board[2] == board[4] == board[6]:
        return "win"
    # full board, no win
    elif board.count("X") == 5:
        return "draw"
    else:
        return "ongoing"


def inbound(time):
    sock.settimeout(time)
    try:
        (reply, address) = sock.recvfrom(1024)
        sock.settimeout(None)
        return reply
    except socket.timeout:
        sock.settimeout(None)
        return "ERROR: No reply received from the client"


def outbound(msg_to_server):
    trials = 0
    max_trials = 9
    # 1s timeout
    sock.settimeout(1.0)
    msg_reply = " "
    # send message to server
    # if no reply is received after 1s, the message will be sent again
    # this procedure is going to be repeated up to 9 times, before warning the user
    while trials < max_trials:
        try:
            sock.sendto(msg_to_server, (SERVER_IP, SERVER_PORT))
            (msg_reply, address) = sock.recvfrom(1024)
            sock.settimeout(None)
            break;
        except socket.timeout:
            trials += 1
        print("iter")
    sock.settimeout(None)
    print("outbound message reply " + msg_reply)
    if trials == max_trials:
        return "ERROR: unable to reach server"
    elif msg_reply == "OK":
        return "OK"
    elif msg_reply.split('$')[0] == "NOK":
        return msg_reply.split('$')[1]
    elif msg_reply.split('$')[0] == "OK":
        return "OK"


while True:
    print("Input message to server below.")
    ins, outs, exs = select.select(inputs, [], [])
    # select devolve para a lista ins quem esta a espera de ler
    for i in ins:
        # i == sys.stdin - alguem escreveu na consola, vamos ler e enviar
        if i == sys.stdin:
            # sys.stdin.readline() le da consola
            msg_temp = sys.stdin.readline()
            msg_temp = msg_temp.replace('\n', '')
            msg = msg_temp.split(' ')

            if msg[0] == "register":
                if status != 0:
                    print("ERROR: You're already registered with the server")
                else:
                    register(msg)
            elif msg[0] == "unregister":
                if status == 0:
                    print("ERROR: You're not registered with the server")
                elif status == 2:
                    print("ERROR: You must finish your game first")
                else:
                    unregister(msg)
            elif msg[0] == "list":
                print("requesting list...")
                list_request()
            elif msg[0] == "invite":
                if status == 0:
                    print("ERROR: You're not registered with the server")
                elif status == 2:
                    print("ERROR: You must finish your game first")
                else:
                    invite(msg)
           # elif msg[0] == "play":
           #     if opponent == " ":
           #         print("You cannot play without choosing an opponent")
           #     elif status == 0:
           #         print("ERROR: You're not registered with the server")
           #     elif status == 2:
           #         print("ERROR: You must finish your game first")
           #     else:
           #         play(msg)

            # envia mensagem da consola para o servidor
        # i == sock - o servidor enviou uma mensagem para o socket
        elif i == sock:
            (msg_temp, addr) = sock.recvfrom(1024)
            ack_client(msg_temp)
            msg = msg_temp.split('$')
            if msg[0] == "invite" and status == 1:
                invite_reply(msg)
            elif msg[0] == "invite" and status == 2:
                print("Not available at the moment. Playing a game")