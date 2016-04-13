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
piece2 = " "


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
    print("ack: " + ack_msg)
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
        if len(l[j].split(':'))== 1:
            return
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
            global piece2
            piece2 = "O"
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
    if choice == "Y\n" or choice == "y\n" or choice == "\n":
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
            global piece2
            piece2 = "X"
            ttt_start_game()
            ttt_print()
            play_wait()
        else:
            print(result)
            return
    elif choice == "N\n" or choice == "n\n":
        outbound(reply_msg_n)
        return
    return


def ttt_start_game():
    global board
    board = []
    j = 0
    while j <= 8:
        board.append(j)
        j += 1


def ttt_print():
    print(" ")
    print(" " + str(board[0]) + " | " + str(board[1]) + " | " + str(board[2]))
    print(" --- --- ---")
    print(" " + str(board[3]) + " | " + str(board[4]) + " | " + str(board[5]))
    print(" --- --- ---")
    print(" " + str(board[6]) + " | " + str(board[7]) + " | " + str(board[8]))
    print(" ")


def ttt_play():
    ttt_print()
    print("Make your move (0-8)")
    move = sys.stdin.readline()
    place = int(move)
    play(place)
    return


def play(place):

    msg_to_server = "play$" + name + ";" + opponent + ";" + str(place)
    result = outbound(msg_to_server)

    if result == "OK":
        board[place] = piece
        ttt_print()
        result = play_wait()
        if result == "quit":
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            update_status(1)
            return
    else:
        print(result)
        ttt_play()


def play_wait():

    ok_msg = "OK$" + name + ";" + opponent
    nok_msg = "NOK$" + name + ";" + opponent + ";" + "Invalid move"
    end_msg_v = "fim$" + name + ";" + opponent + ";" + "You WIN!"
    end_msg_d = "fim$" + name + ";" + opponent + ";" + "It's a Draw"
    game_state = 0

    # wait for opponent to play
    print("Waiting for the other player to make a move...")
    while True:
        # check if the game is over
        if game_state == 1 or game_state == 2:
            ttt_print()
            if game_state == 1:
                print("Game ended, You lost!")
            if game_state == 2:
                print("Game ended, it's a draw!")
            print("quitting game...")
            update_status(1)
            break

        # result = inbound(1000.0)
        (result, address) = sock.recvfrom(1024)
        print("jogada recebida: " + result)

        if result.split('$')[0] == "fim":
            ack_client(result)
            print("Game ended. " + result.split('$')[1].split(';')[2])
            print("quitting game...")
            update_status(1)
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            break

        place = int(result.split('$')[1].split(';')[2])

        if result.split('$')[0] == "play":
            if board[place] == "X" or board[place] == "O":
                sock.sendto(nok_msg, (SERVER_IP, SERVER_PORT))
                # continue to wait
                continue
            else:
                board[place] = piece2
                sock.sendto(ok_msg, (SERVER_IP, SERVER_PORT))
                game_state = check_if_win()
                if game_state == 1:
                    outbound(end_msg_v)
                    continue
                elif game_state == 2:
                    outbound(end_msg_d)
                    continue
                elif game_state == 0:
                    ttt_play()
        else:
            print("result")
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            # clean game board
            ttt_start_game()
            print("quitting game... CHECK THIS!")

        # leaving the game being played, no matter the reason
        return "quit"


def check_if_win():
    # lines
    if board[0] == board[1] == board[2]:
        return 1
    elif board[3] == board[4] == board[5]:
        return 1
    elif board[6] == board[7] == board[8]:
        return 1
        # columns
    elif board[0] == board[3] == board[6]:
        return 1
    elif board[1] == board[4] == board[7]:
        return 1
    elif board[2] == board[5] == board[8]:
        return 1
    # diagonals
    elif board[0] == board[4] == board[8]:
        return 1
    elif board[2] == board[4] == board[6]:
        return 1
    # full board, no win
    elif board.count("X") == 5:
        return 2
    else:
        return 0


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
            break
        except socket.timeout:
            trials += 1
        print("iter")
    sock.settimeout(None)
    print("outbound message received " + msg_reply)
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
            elif msg[0] == "quit":
                msg[0] = "unregister"
                unregister(msg)
                quit()                
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