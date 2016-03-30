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

from influxdb import InfluxDBClient
import socket
import select
import sys
import signal


# The broadcast_message() function forwards the message msg
# received from sock to all the other connected users.
def broadcast_message(sender_sock, sender_name, msg_content):

    # If the sender username is equal to DUMMYUSERNAME, then the message won't be stored into InfluxDB.
    if sender_name != DUMMY_USERNAME:
        json_body = [
            {
                "measurement": MEASUREMENT_NAME,
                "tags": {
                    "username": sender_name
                },
                "fields": {
                    "value": msg_content
                }
            }
        ]
        # Send the message to InfluxDB
        influxdb_client.write_points(json_body)

    # Forward the message to all other users.
    for dest_sock in list_channels:
        # Clearly msg is not sent neither to the server itself nor to the initial sender.
        if dest_sock != server_socket and dest_sock != sender_sock:
            # The try-except construct is used to handle broken channels (e.g., when a user pressed "Ctrl+C")
            try:
                if sender_name != DUMMY_USERNAME:
                    msg_to_deliver = "<"+sender_name+">: "+msg_content
                else:
                    msg_to_deliver = msg_content
                dest_sock.send(msg_to_deliver.encode('utf-8'))
            except:
                dest_sock.close()
                print("DEBUG: removing socket in broadcasting "+str(dest_sock))
                list_channels.remove(dest_sock)


# signal_handler function is called when a SIGINT signal is detected (e.g., Ctrl+C have been pressed)
def signal_handler(signal, frame):
    print('\nInfluxChat Server will be terminated.')
    broadcast_message(server_socket, DUMMY_USERNAME, MSG_END)
    server_socket.close()
    sys.exit()

# Main function
if __name__ == "__main__":
    print("+---------------------+")
    print("| InfluxChat - Server |")
    print("+---------------------+")

    # Constants for interacting with InfluxDB.
    DB_NAME = "PervSystPers"
    DB_ADDRESS = "localhost"
    DB_PORT = 8086
    MEASUREMENT_NAME = "influxchat"
    RET_POL_NAME = 'del_4_weeks'
    RET_POL_PERIOD = '4w'
    RET_POL_N_COPY = 1
    CONT_QUERY = """create continuous query cq_30m on PervSystPers
                    begin   select count(value) as num_msg
                            into PervSystPers.\"default\".downsampled_msg
                            from influxchat
                            group by time(30m)
                    end"""

    print("Connecting to InfluxDB database...")
    influxdb_client = InfluxDBClient(host=DB_ADDRESS, port=DB_PORT, database=DB_NAME)

    print("Done.")

    print("Setting up continuous queries and retention policies...")
    # Set up the continuous query
    try:
        result_db = influxdb_client.query(CONT_QUERY)
    except:
        print("Note: continuous query already exists.")

    # Set up retention policy
    resultdb = influxdb_client.create_retention_policy(RET_POL_NAME, RET_POL_PERIOD,
                                                       RET_POL_N_COPY, DB_NAME, default=True)
    print("Done.")

    print("Setting up socket...")
    # List to keep track of socket descriptors
    list_channels = []

    # Constants for socket interactions.
    MSG_END = "QUIT"
    RECV_BUFFER_SIZE = 4096
    CHAT_SERVER_ADDR = "127.0.0.1"
    CHAT_SERVER_PORT = 5050
    ALLOWED_CONNECTIONS = 10
    DUMMY_USERNAME = ""

    # The server keeps track of the name associated to each currently connected user
    username_addr_map = {}

    # Set up the signal handler for Ctrl+C.
    signal.signal(signal.SIGINT, signal_handler)

    # Create socket for InfluxChat Server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", CHAT_SERVER_PORT))
    server_socket.listen(ALLOWED_CONNECTIONS)

    # Add server socket to the list of readable channels
    list_channels.append(server_socket)

    print("Done.")
    print("Waiting for connections on port " + str(CHAT_SERVER_PORT) + ".")

    while True:
        # Use select() for getting the channels that are ready to be read
        read_sockets, write_sockets, err_sockets = select.select(list_channels, [], [])

        for read_sock in read_sockets:
            # If read_sock is the server socket, then a new inbound connection occurred
            if read_sock == server_socket:
                print("DEBUG: I'm receiving from server socket.")
                read_sock_fd, addr = server_socket.accept()
                list_channels.append(read_sock_fd)

                name_received = False
                new_username = ''
                while not name_received:
                    read_sockets_name, write_sockets_name, err_sockets_name = select.select([read_sock_fd], [], [])

                    for read_name_sock in read_sockets_name:
                        if read_name_sock != read_sock_fd:
                            print("DEBUG: Error while receiving username.")
                        else:
                            new_username = read_name_sock.recv(RECV_BUFFER_SIZE).decode()
                            # We need to remove the "\n" at the end.
                            new_username = new_username[0:len(new_username)-1]
                            # Add the username to a map for future usage.
                            username_addr_map[read_name_sock] = new_username
                            name_received = True

                # Notify to all users that someone joined the conversation
                broadcast_message(read_sock_fd, DUMMY_USERNAME, "--- %s joined the conversation ---" % new_username)
                print("--- %s joined the conversation ---" % new_username)

            # Else, the value to be read is a new message sent by some user
            else:
                print("DEBUG: I'm receiving from users.")

                # Get the username related to the socket.
                sender_username = username_addr_map[read_sock]

                # the try-except construct is used to handle
                # "Connection reset by peer" exceptions in Windows
                try:
                    msg = read_sock.recv(RECV_BUFFER_SIZE).decode()
                    if msg and len(str(msg)) > 0:

                        # If the user sent MSG_END, then he/she has left the room.
                        if str(msg) == MSG_END:
                            # print("--- <"+str(read_sock_fd.getpeername())+"> is now offline ---")
                            print("--- <"+sender_username+"> is now offline ---")
                            broadcast_message(read_sock, DUMMY_USERNAME, "--- <"+sender_username+"> is now offline ---")

                            # Close the socket, and remove it from the list of channels we're listening to.
                            read_sock_fd.close()
                            list_channels.remove(read_sock)
                            # Also remove the username from the map.
                            del username_addr_map[read_sock]

                        # Else, simply broadcast the inbound message.
                        else:
                            broadcast_message(read_sock, sender_username, str(msg))
                    else:
                        print("--- <"+sender_username+"> is now offline ---")
                except:
                    print("--- <"+sender_username+"> is now offline ---")
                    broadcast_message(read_sock_fd, DUMMY_USERNAME, "--- <"+sender_username+"> is now offline ---")
                    read_sock_fd.close()
                    print("DEBUG: removing socket in except "+str(read_sock_fd))
                    list_channels.remove(read_sock_fd)
                    continue

    server_socket.close()
