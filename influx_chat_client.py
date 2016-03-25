"""
Created on Wed Mar 16 18:10:35 2016
@author: Roberto Gaudenzi
+------------------------------------------------------+
|             Sapienza - Università di Roma            |
| Master of Science in Engineering in Computer Science |
|                   Pervasive Systems                  |
|                     a.y. 2015-16                     |
|               Introduction to InfluxDB               |
|               InfluxDB-Python Example                |
|                 InfluxChat - Client                  |
+------------------------------------------------------+
"""

import socket
import select
import sys
import signal


def prompt():
    sys.stdout.write("<You>: ")
    sys.stdout.flush()


def signal_handler(signal, frame):
    print('\nInfluxChat will be terminated. Goodbye!')
    sock.send(MSG_END.encode('utf-8'))
    sys.exit()

# Main function
if __name__ == "__main__":

    MSG_END = "QUIT"
    RECV_BUFFER_SIZE = 4096
    CHAT_SERVER_ADDR = "127.0.0.1"
    CHAT_SERVER_PORT = 5050

    signal.signal(signal.SIGINT, signal_handler)

    print("+---------------------+")
    print("| InfluxChat - Client |")
    print("+---------------------+")
    print("Welcome to InfluxChat! Please type your name:")
    username = sys.stdin.readline()

    print("Trying to connect to InfluxChat Server...")

    # Create the socket to connect to InfluxChat Server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)

    # Try to connect to the InfluxChat Server
    try:
        sock.connect((CHAT_SERVER_ADDR, CHAT_SERVER_PORT))
        # TODO it would be nice if the users can use their name instead of their address
        sock.send(username.encode('utf-8'))
    except:
        print("Unable to reach InfluxChat Server. Try again later.")
        sys.exit()



    print("Connection succeeded. Type \'QUIT\' or press \'Ctrl+C\' to terminate.")
    # If the client succeeds in connecting to the server, then allow to the user to chat.
    prompt()

    # Control inbound traffic both from the socket and from the user(that writes on standard input)
    list_channels = [sys.stdin, sock]

    while True:
        # Use select() for getting the channels that are ready to be read
        read_sockets, write_sockets, err_sockets = select.select(list_channels, [], [])

        for read_sock in read_sockets:
            # If the readable channel is the socket, then a new message occurred
            if read_sock == sock:
                # If there is no message, then the connection has been interrupted
                try:
                    msg = sock.recv(RECV_BUFFER_SIZE).decode()
                    if msg and len(str(msg)) > 0:
                        print("\nDEBUG: message received")
                        if str(msg) == "QUIT":
                            print("InfluxChat Server has been shut down. Sorry for the inconvenience.")
                            sys.exit()
                        else:
                            print(str(msg))
                            prompt()
                except:
                    print("Disconnected from InfluxChat Server. Sorry for the inconvenience.")
                    sys.exit()
            # Else, the user wrote a new message: send it to the InfluxChat Server
            else:
                msg = sys.stdin.readline()
                sock.send(msg.encode('utf-8'))
                print("DEBUG: message sent")
                if msg == "QUIT":
                    signal_handler()
                else:
                    prompt()
