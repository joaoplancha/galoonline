import socket
import sys
import select

# Possible commands:
# register <name>
# unregister
# list
# invite <name>
# quit


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


# updates the status of the client
def update_status(new):
    global status
    status = new


# in game mode, updates the status of the opponent
def update_opponent(client):
    global opponent
    opponent = client


# Acknowledge message (client - server comm)
def ack_server():
    # send the ack to server
    sock.sendto("OK", (SERVER_IP, SERVER_PORT))


# Acknowledge message (client - client comm)
# Receives original message as argument
# Constructs the ack message with elements received
# Sends message to server (and server will relay to client)
def ack_client(m):
    arg2 = m.split('$')[1].split(';')[0]
    arg1 = m.split('$')[1].split(';')[1]
    ack_msg = "OK$" + arg1 + ";" + arg2
    # send the ack to client (through server relay)
    sock.sendto(ack_msg, (SERVER_IP, SERVER_PORT))


# Registers player on the server
def register(m):
    msg_to_server = m[0] + "$" + m[1]
    result = outbound(msg_to_server)

    # Check if ACK from the server was received by outbound function
    if result == "OK":
        # If ACK was received, update client status to say it's free
        update_status(1)
        # Puts the name in the "name" global variable.
        global name
        name = m[1]
        print("Registered with the name: " + name)
    else:
        # If ACK was not received, prints the reason why
        print(result)


# Unregisters the player from the server
def unregister(m):
    msg_to_server = m[0]
    result = outbound(msg_to_server)

    # Check if ACK from the server was received by outbound function
    if result == "OK":
        # If ACK was received, update client status to unregistered status
        update_status(0)
        global name
        # Player name is reset to empty string
        name = " "
    else:
        # If ACK was not received, prints the reason why
        print(result)


# Requests the player list from the server
# The successful reception of the list is used as ACK from the server
# therefore, the outbound function is not used here
def list_request():
    # Set the timeout to 1s
    # If nothing is received from the server side, it tries again 10 times
    trials = 0
    max_trials = 9
    sock.settimeout(1.0)
    msg_reply = ""

    while trials < max_trials:
        try:
            sock.sendto("list", (SERVER_IP, SERVER_PORT))
            (msg_reply, address) = sock.recvfrom(1024)
            # If a message is received, sends ACK to server
            ack_server()
            break
        except socket.timeout:
            trials += 1
    # Remove the timeout from the socket. It's back blocking
    sock.settimeout(None)

    # If maximum of trials was reached without any reply, returns an error to user
    if trials == max_trials:
        print("ERROR: unable to reach server")
    # Otherwise, prints the client list
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
            print(namel + "\t\t\t" + statusl)
            j += 1
        print("-------------------------------")


# Invites a certain player to play
def invite(m):
    # invite message formation to send through server to the client we want to invite
    invite_msg = m[0] + "$" + name + ";" + m[1]
    # send the message to client through server
    # it's the server responsibility to interpret and relay as appropriate
    # use of outbound function implies the need for an ACK reply
    result = outbound(invite_msg)
    # If ACK is received, then the client assumes the message was well received
    # by the invitee
    if result == "OK":
        print("invitation received by opponent. waiting for reply")
        # It will now wait for the invitee response
        # outbound function is not used in this case
        (reply, address) = sock.recvfrom(1024)
        # There is no timeout here. It needs an action from the invitee
        # Checks if the received response is positive
        # result = inbound(60.0)
        if reply.split('$')[0] == "inviteR" and reply.split('$')[1].split(';')[0] == "Y":
            # Informs the server that client is busy
            outbound("busy")
            # Sends the reply ACK to invitee
            ack_client("OK$" + m[1] + ";" + name)
            print("Invitation accepted")
            # Updates own status and opponent status (locally)
            update_status(2)
            update_opponent(m[1])
            # Defines own piece as 'X' and opponent piece as 'O'
            global piece
            piece = "X"
            global piece2
            piece2 = "O"
            # Starts the game creating a new board and entering play function
            ttt_start_game()
            ttt_play()
        # If the reply is negative
        elif reply.split('$')[0] == "inviteR" and reply.split('$')[1].split(';')[0] == "N":
            # Informs the opponent that the message was received
            ack_client("OK$" + m[1] + ";" + name)
            print("Invitation not accepted")
            return
        else:
            print(result)
    else:
        print(result)


# If client received an invite to play, it enters this function
# Takes care of the response and follow up action
def invite_reply(m):

    invite_msg = m[1].split(';')
    # Possible reply message definition
    reply_msg_y = "inviteR$Y;" + invite_msg[1] + ";" + invite_msg[0]
    reply_msg_n = "inviteR$N;" + invite_msg[1] + ";" + invite_msg[0]

    print(invite_msg[0] + " is inviting you to play")
    print("Do you accept the invitation? (Y/N)")

    choice = sys.stdin.readline()
    if choice == "Y\n" or choice == "y\n" or choice == "\n":
        # If positive sends the reply through the outbound function
        # therefore is waiting for a reply
        result = outbound(reply_msg_y)
        if result == "OK":
            # If the other inviter confirms the reception, 
            # informs the server, updates all status,
            # defines the pieces as 'O' for client and 'X' for the inviter
            # and enters the waiting for play function
            outbound("busy")
            update_status(2)
            update_opponent(invite_msg[0])
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
        # If negative
        outbound(reply_msg_n)
        return
    return


# Creates a new empty board
def ttt_start_game():
    global board
    board = []
    j = 0
    while j <= 8:
        board.append(j)
        j += 1


# Prints the board to the screen
def ttt_print():
    print(" ")
    print(" " + str(board[0]) + " | " + str(board[1]) + " | " + str(board[2]))
    print(" --- --- ---")
    print(" " + str(board[3]) + " | " + str(board[4]) + " | " + str(board[5]))
    print(" --- --- ---")
    print(" " + str(board[6]) + " | " + str(board[7]) + " | " + str(board[8]))
    print(" ")


# Receives the play from the client and executes it using play function
def ttt_play():
    while True:
        ttt_print()
        print("Make your move (0-8)")
        print("enter 9 to give up")
        move = sys.stdin.readline()
        try : 
            place = int(move)
            play(place)
            return
        except:
            print("Invalid play!")


# Function that will execute the selected play
def play(place):

    if place == 9:
        quit_msg = "quit$" + name + ";" + opponent
        # message to opponent
        result = outbound(quit_msg)
        update_status(1)
        # message to server
        outbound("free")
        print("you've given up. quitting...")
        # after server confirms reception, quits
        return "quit"
    
    msg_to_server = "play$" + name + ";" + opponent + ";" + str(place)
    result = outbound(msg_to_server)

    # If the ACK is received, updates own board, prints result on board and waits
    if result == "OK":
        board[place] = piece
        ttt_print()
        result = play_wait()
        # If the reply from the other side is quit, quits game
        if result == "quit":
            # message to server
            outbound("free")
            # after server confirms reception, quits
            update_status(1)
            return
    # If no OK (ack) or quit is received, gives the reason and client can play again
    else:
        print(result)
        ttt_play()


# Function used to wait for the opponent to play
# It also verifies if the play is valid or not and checks if someone won or it's a draw
def play_wait():

    # Message definitions
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
        # Waits for opponent's play
        (result, address) = sock.recvfrom(1024)

        # case the opponent quits the ongoing game
        if result.split('$')[0] == "quit":
            ack_client(result)
            print("the other player gave up. quitting game...")
            outbound("free$" + result.split('$')[1])
            # sock.sendto("free", (SERVER_IP, SERVER_PORT))
            update_status(1)
            break

        # game is ended, quit game and update server and self
        if result.split('$')[0] == "fim":
            ack_client(result)
            print("Game ended. " + result.split('$')[1].split(';')[2])
            print("quitting game...")
            outbound("free")
            update_status(1)
            # CHANGE this to outbound to make sure server updates
            break

        # If the game is not over...
        place = int(result.split('$')[1].split(';')[2])

        if result.split('$')[0] == "play":
            # If play is not valid
            if place > 9 or board[place] == "X" or board[place] == "O":
                # no need to send through outbound, it's dealt with on the client side
                sock.sendto(nok_msg, (SERVER_IP, SERVER_PORT))
                # continue to wait
                continue
            # If play is valid
            else:
                board[place] = piece2
                sock.sendto(ok_msg, (SERVER_IP, SERVER_PORT))
                game_state = check_if_win()
                # End game verification and message sending
                if game_state == 1:
                    outbound(end_msg_v)
                    continue
                elif game_state == 2:
                    outbound(end_msg_d)
                    continue
                elif game_state == 0:
                    ttt_play()
        # If something bad happens, it clears the game board and quits the game
        # Also warns the server
        # CHANGE to outbound
        else:
            sock.sendto("free", (SERVER_IP, SERVER_PORT))
            # clean game board
            ttt_start_game()
            print("quitting game... CHECK THIS!")

        # leaving the game being played, no matter the reason
        return "quit"


# Auxiliary function to check if opponent has won
# returns 1 if the opponent has won, 2 if it's a draw and 0 in any other case
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


# not used for now
def inbound(time):
    sock.settimeout(time)
    try:
        (reply, address) = sock.recvfrom(1024)
        sock.settimeout(None)
        return reply
    except socket.timeout:
        sock.settimeout(None)
        return "ERROR: No reply received from the client"


# Key function to client - client comm
# Sends a message to other client through server
# Waits for the ACK from the other side
# It has a timeout of 1s, and 10 times to retry.
# Returns the received message or error result
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
    sock.settimeout(None)
    if trials == max_trials:
        return "ERROR: unable to reach server"
    elif msg_reply == "OK":
        return "OK"
    elif msg_reply.split('$')[0] == "NOK":
        return msg_reply.split('$')[1]
    elif msg_reply.split('$')[0] == "OK":
        return "OK"


# Main program cycle. Alternated between receiving commands from keyboard and
# invite messages from other clients (through server)
while True:
    print("Input message to server below.")
    ins, outs, exs = select.select(inputs, [], [])
    # select devolve para a lista ins quem esta a espera de ler
    for i in ins:
        # i == sys.stdin - alguem escreveu na consola, vamos ler e enviar
        if i == sys.stdin:
            # Formats the received command as appropriate
            msg_temp = sys.stdin.readline()
            msg_temp = msg_temp.replace('\n', '')
            msg = msg_temp.split(' ')

            # Keyboard input: Self explanatory
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
            	if status != 0:
                	msg[0] = "unregister"
                	unregister(msg)
                quit()
        # If received something from the network it will continue here.
        elif i == sock:
            (msg_temp, addr) = sock.recvfrom(1024)
            ack_client(msg_temp)
            msg = msg_temp.split('$')
            # If the message is invite, it will enter the invite_reply function
            if msg[0] == "invite" and status == 1:
                invite_reply(msg)
            # unless client is busy, in which case replies not available
            # this doesn't actually do anything....... :-(
            elif msg[0] == "invite" and status == 2:
                print("Not available at the moment. Playing a game")