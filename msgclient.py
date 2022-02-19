import socket
import threading
import json
from datetime import datetime


# JSON FORMAT:
# From Host: NEWMSG SENDER TIMESTAMP | ARGS: MSG
# From Client: SENDMSG RECEIVER TIMESTAMP | ARGS: MSG (cmd ver: send thomas hello)

def write(groups_lock):
    global groups
    while True:
        msg_input = input()
        cmd, rest = msg_input.split(' ', 1)
        if cmd[0] == "send":
            sender, msg = rest.split(' ', 1)
            data = json.dumps({'cmd': ['SENDMSG', sender, datetime.now()], 'args': msg})
            client.send(data.encode())


def receive(groups_lock):
    global groups
    data = client.recv(2048).decode()
    init_cmd = json.loads(data)
    if init_cmd['cmd'][0] == 'NICK':
        cmd = json.dumps({'cmd': ['NAME'], 'args': username})
        try:
            client.send(cmd.encode())
        except:
            print("Error occured.")
            client.close()
            return
    else:
        print("Error in establishing username with host. Closed connection.")
        client.close()
        return
    while True:
        try:
            data = client.recv(2048).decode()
            data_loaded = json.loads(data)
            cmd = data_loaded['cmd']
            if cmd[0] == 'NEWMSG':
                sender = cmd[1]
                timestamp = cmd[2].strftime("%Y-%m-%d %H:%M:%S")
                print(f"{str(sender)} [{timestamp}]: {data_loaded['args']}")
            elif cmd[0] == 'ERROR':
                print(data_loaded['args'])
            elif cmd[0] == 'OFFLINEMSG':
                print(
                    f"\n\***** ALERT: {cmd[1]} is offline right now. The message will be sent again once it is online. *****/\n")
        except:
            print("Error occured. Closing connection now....")
            client.close()
            return


client = socket.socket()
groups_lock = threading.Lock()
groups = {}
username = input("Enter your username (it must have no spaces!): ")

while True:
    host = input("Enter host IP address: ")
    port = input("Enter host port: ")

    try:
        client.connect((host, port))
        break
    except:
        print("Failed to connect. Please retry.\n")

receive_thread = threading.Thread(target=receive, args=(groups_lock,))
receive_thread.start()

write_thread = threading.Thread(target=write, args=(groups_lock,))
write_thread.start()
