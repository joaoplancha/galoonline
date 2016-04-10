import socket
BUFFER_SIZE = 1024
ClientMsg = raw_input('Message to send:')
ClientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ClientSock.connect(('localhost',5005))
ClientSock.send(ClientMsg)
print "Message to server :", ClientMsg
ServerMsg = ClientSock.recv(BUFFER_SIZE)
print "Message from server: ", ServerMsg
ClientSock.close()