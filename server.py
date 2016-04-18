import socket

# INICIALIZACAO

# Server port definition
SERVER_PORT = 12000

# UDP socket creation for client communication
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('', 12000))

# Lists to store information about client name and ip address
addressList = {}  # dict: nome -> endereco, status. Ex: addrs["user"]=('127.0.0.1',17234)
clientList = {}  # dict: endereco -> nome, status. Ex: clients[('127.0.0.1',17234)]="user"
statusList = {} # dict: client -> status

#  message list
msg_invalid = "Command not recognized"
msg_OK = "OK"
msg_nOK_register = "NOK$name exists"
msg_nOK_unregister = "NOK$name doesn't exist"
msg_nOK_unknownclient = "NOK$requested player is not connected to the server"
msg_nOK_busy = "NOK$Player is busy"
msg_list = "LIST$"


# Invalid option selected - command not recognized
def invalid(address):
    server.sendto(msg_invalid, address)


# Client register
def register(client, address):
    # if it's not registered already
    if not client in addressList and not address in clientList:
        addressList[client] = address
        clientList[address] = client
        statusList[client] = "free"
        server.sendto(msg_OK, address)
    # it it exists, reply with nOK message
    else:
        server.sendto(msg_nOK_register, address)


# Unregister client
def unregister(address):
    client = clientList[address]
    if client in addressList:
        del addressList[client]
        del statusList[client]
        del clientList[address]
        server.sendto(msg_OK, address)
    else:
        server.sendto(msg_nOK_unregister, address)


# Client List - returns the client list
def client_list(address):
    l = []
    msg_str = ""
    for keys, values in statusList.items():
        msg_str = keys + ":"
        msg_str += values
        l.append(str(msg_str))
    msg_out = msg_list + str(l)[1:len(str(l))-1]
    outbound(msg_out, address)


# used to send messages that need to wait for an ack from the client
def outbound(msg_to_client, address):
    trials = 0
    max_trials = 9
    # 1s timeout
    server.settimeout(1.0)
    msg_reply = ""

    while trials < max_trials:
        try:
            server.sendto(msg_to_client, address)
            (msg_reply, address) = server.recvfrom(1024)
            break
        except socket.timeout:
            trials += 1

    server.settimeout(None)

    if trials == max_trials:
        print("ERROR: did not receive ACK from client")


# Client to Client message relay function
def forward(name, message):
    # message is already well formed (invite$player1;player2)
    # ACK messages will use this function as well. their format will not be changed
    # it's the client responsibility to create coherent messages
    # server doesn't care if the message is received or not. Client needs to take care of that.
    # in client2client communication, the server is just a relay between clients
    if name in addressList:
        message_relay = message
        address = addressList[name]
        server.sendto(message_relay, address)


# Set client as busy
def set_busy(address):
    statusList[clientList[address]] = "busy"
    server.sendto(msg_OK, address)



# Set client as free
def set_free(address):
    statusList[clientList[address]] = "free"
    server.sendto(msg_OK, address)
    server.sendto(msg_OK, address)



# MAIN BODY
while True:
    (msg, addr) = server.recvfrom(1024)
    # get the command
    cmds = msg.decode().split('$')
    if cmds[0] == "register":
        register(cmds[1], addr)
    elif cmds[0] == "unregister":
        unregister(addr)
    elif cmds[0] == "list":
        client_list(addr)
    elif cmds[0] == "invite":
        # check if requested player exists in the server
        if cmds[1].split(';')[1] in addressList:
            # check if it's free
            if statusList[cmds[1].split(';')[1]] == "free":
                forward(cmds[1].split(';')[1], msg)
            else:
                server.sendto(msg_nOK_busy, addr)
        else:
            server.sendto(msg_nOK_unknownclient, addr)
    elif cmds[0] == "inviteR":
         forward(cmds[1].split(';')[2], msg)
    elif cmds[0] == "OK" or cmds[0] == "NOK" or cmds[0] == "play" or cmds[0] == "fim" or cmds[0] == "quit":
        forward(cmds[1].split(';')[1], msg)
    elif cmds[0] == "busy":
        set_busy(addr)
    elif cmds[0] == "free":
        set_free(addr)
    elif cmds[0] == "kill":
        break
    else:
        invalid(addr)

server.close()
