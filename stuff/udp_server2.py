import socket
#ServerMsg="Nice to meet you"
ServerSock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
ServerSock.bind(('',7005))
(ClientMsg,(ClientIP,ClientPort))=ServerSock.recvfrom(100)
print "Client Message:",ClientMsg
ServerSock.sendto(ClientMsg,(192.168.66.101,2012))
ServerSock.close()