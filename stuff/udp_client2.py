import socket
ClientMsg = raw_input('Message to send:')
ClientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ClientSock.sendto(ClientMsg, ('172.199.66.1',7005))
print "Message to server :", ClientMsg
(ServerMsg,(ServerIP,ServerPort))= ClientSock.recvfrom (100)
print "Message from server: ", ServerMsg
ClientSock.close()