import socket
#ServerMsg="Nice to meet you"
BUFFER_SIZE = 1024
ServerSock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
ServerSock.bind(('',5005))
ServerSock.listen(10)
while 1:
	NewClientSock, addr = ServerSock.accept()
	print "Connection address: ", addr
	ClientMsg = NewClientSock.recv(BUFFER_SIZE)
	if ClientMsg == "q": break
	print "Client Message:",ClientMsg
	NewClientSock.send(ClientMsg)
print "quitting"
NewClientSock.close()