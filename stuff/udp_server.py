import socket
#ServerMsg="Nice to meet you"
ServerSock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
ServerSock.bind(('',5005))
(ClientMsg,(ClientIP,ClientPort))=ServerSock.recvfrom(100)
print "Client Message:",ClientMsg
ServerSock.sendto(ClientMsg,(ClientIP,ClientPort))
ServerSock.close()