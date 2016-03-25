"""
Created on Wed Mar 16 18:05:28 2016
@author: Roberto Gaudenzi
+------------------------------------------------------+
|             Sapienza - Università di Roma            |
| Master of Science in Engineering in Computer Science |
|                   Pervasive Systems                  |
|                     a.y. 2015-16                     |
|               Introduction to InfluxDB               |
|               InfluxDB-Python Example                |
|                 InfluxChat - Server                  |
+------------------------------------------------------+
"""

# from influxdb import InfluxDBClient
import socket
import select
import sys
import signal


# The broadcast_message() function forwards the message msg
# received from sock to all the other connected users.
def broadcast_message(sender_sock, msg_content):
    # TODO before (?) sending a message to clients, we have to store it into InfluxDB
    print("DEBUG: broadcasting %s" % msg_content)
    for dest_sock in list_channels:
        # Clearly msg is not sent (again) neither to the sender itself nor to the initial sender.
        if dest_sock != server_socket and dest_sock != sender_sock:
            print("DEBUG: broadcasting; sending message to %s" % sender_sock)
            # The try-except construct is used to handle broken channels (e.g., when a user pressed "Ctrl+C")
            try:
                dest_sock.send(msg_content.encode('utf-8'))
            except:
                dest_sock.close()
                list_channels.remove(dest_sock)


def signal_handler(signal, frame):
    print('InfluxChat Server will be terminated.')
    broadcast_message(server_socket, MSG_END)
    server_socket.close()
    sys.exit()

# Main function
if __name__ == "__main__":

    DBNAME = "InfluxChatTest"
    DB_ADDRESS = "127.0.0.1"
    DB_PORT = 8086

    # client = InfluxDBClient(database=DBNAME)

    # List to keep track of socket descriptors
    list_channels = []
    MSG_END = "QUIT"
    RECV_BUFFER_SIZE = 4096
    CHAT_SERVER_ADDR = "127.0.0.1"
    CHAT_SERVER_PORT = 5050
    ALLOWED_CONNECTIONS = 10

    # The server keeps track of the name associated to each currently connected user
    username_addr_map = {}

    signal.signal(signal.SIGINT, signal_handler)

    # Create socket for InfluxChat Server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", CHAT_SERVER_PORT))
    server_socket.listen(ALLOWED_CONNECTIONS)

    # Add server socket to the list of readable channels
    list_channels.append(server_socket)

    print("+---------------------+")
    print("| InfluxChat - Server |")
    print("+---------------------+")
    print("Waiting for connections on port " + str(CHAT_SERVER_PORT) + ".")

    i = 0
    while True:
        print(list_channels)
        # Use select() for getting the channels that are ready to be read
        read_sockets, write_sockets, err_sockets = select.select(list_channels, [], [])

        for read_sock in read_sockets:
            # If read_sock is the server socket, then a new inbound connection occurred
            if read_sock == server_socket:
                print("DEBUG: I'm receiving from server socket. "+str(i))
                read_sock_fd, addr = server_socket.accept()
                list_channels.append(read_sock_fd)
                # TODO It would be nice to use clients' names instead of their IP addresses
                # new_username = read_sock.recv(RECV_BUFFER_SIZE)
                # username_addr_map[addr] = new_username
                # Notify to all users that someone joined the conversation
                broadcast_message(read_sock_fd, "--- [%s:%s] joined the conversation ---" % (addr[0], addr[1]))
                print("--- [%s:%s] joined the conversation ---" % (addr[0], addr[1]))
                i += 1
            # Else, the value to be read is a new message sent by some user
            else:
                print("DEBUG: I'm receiving from users. "+str(i))
                # the try-except construct is used to handle
                # "Connection reset by peer" exceptions in Windows
                try:
                    msg = read_sock.recv(RECV_BUFFER_SIZE).decode()
                    if msg and len(str(msg)) > 0:
                        if str(msg) == "QUIT":
                            print("--- <"+str(read_sock_fd.getpeername())+"> is now offline ---")
                            broadcast_message(read_sock_fd, "--- <"+str(read_sock_fd.getpeername())+"> is now offline ---")
                            read_sock_fd.close()
                            list_channels.remove(read_sock_fd)
                        else:
                            broadcast_message(read_sock, "<"+str(read_sock_fd.getpeername())+">: " + str(msg))
                    else:
                        print("DEBUG: else branch in receiving messages. "+str(i))
                        print("--- <"+read_sock_fd.getpeername()+"> is now offline ---")
                except:
                    print("--- <"+str(read_sock_fd.getpeername())+"> is now offline ---")
                    broadcast_message(read_sock_fd, "--- <"+str(read_sock_fd.getpeername())+"> is now offline ---")
                    read_sock_fd.close()
                    list_channels.remove(read_sock_fd)
                    continue

    server_socket.close()
