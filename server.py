import socket

# Recebe no porto SERVER PORT os comandos "IAM <nome>", "HELLO",
#    "HELLOTO <nome>" ou "KILLSERVER"
# "IAM <nome>" - regista um cliente como <nome>
# "HELLO" - responde HELLO ou HELLO <nome> se o cliente estiver registado
# "HELLOTO <nome>" - envia HELLO para o cliente <nome>
# "KILLSERVER" - mata o servidor

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
msg_list = "LIST$"


# Invalid option selected - command not recognized
def invalid(address):
    server.sendto(msg_invalid, address)


# Client register
def register(client, address):
    if not client in addressList and not address in clientList:
        addressList[client] = address
        clientList[address] = client
        statusList[client] = "free"
        server.sendto(msg_OK, address)
    else:
        server.sendto(msg_nOK_register, address)


def unregister(address):
    client = clientList[address]
    if client in addressList:
        del addressList[client]
        del statusList[client]
        del clientList[address]
        server.sendto(msg_OK, address)
    else:
        server.sendto(msg_nOK_unregister, address)


# Client List
def client_list(address):
    l = []
    msg_str = ""
    for keys, values in statusList.items():
        msg_str = keys + ":"
        msg_str += values
        l.append(str(msg_str))
    msg_out = msg_list + str(l)[1:len(str(l))-1]
    outbound(msg_out, address)


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
        print("Invitation: "+ msg)
        # check if requested player exists in the server
        if cmds[1].split(';')[1] in addressList:
            forward(cmds[1].split(';')[1], msg)
        else:
            server.sendto(msg_nOK_unknownclient, addr)
    elif cmds[0] == "inviteR":
        print("Invitation Reply: " + msg)
        forward(cmds[1].split(';')[2], msg)
    elif cmds[0] == "play":
        forward(cmds[1].split(';')[1], msg)
    elif cmds[0] == "OK" or cmds[0] == "NOK":
        #relay client to client ack messages
        forward(cmds[1].split(';')[1], msg)
    elif cmds[0] == "kill":
        break
    else:
        invalid(addr)

server.close()
