import socket
import threading
import json
from datetime import datetime
import argparse


# JSON FORMAT:
# From Host: NEWMSG SENDER TIMESTAMP | ARGS: MSG
# From Host: CACHEDMSG | ARGS: [ith sender timestamp msg]
# From Client: SENDMSG RECEIVER TIMESTAMP | ARGS: MSG (cmd ver: send thomas hello)

def write():
    while True:
        if not receive_thread.is_alive():
            exit(0)
        msg_input = input()
        if msg_input == "quit":
            data = json.dumps({'cmd': ['QUIT']})
            client.send(data.encode())
            exit(0)
        cmd, rest = msg_input.split(' ', 1)
        if cmd == 'send':
            receiver, msg = rest.split(' ', 1)
            if receiver == username:
                print("You can't send message to yourself!")
                continue
            data = json.dumps(
                {'cmd': ['SENDMSG', receiver, str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))], 'args': msg})
            client.send(data.encode())
        elif cmd == 'create':
            if len(rest.split()) < 2:
                print("Error: missing arguments.")
                continue
            group_name, members = rest.split(' ', 1)
            members = members.split()
            if username in members:
                members.remove(username)
                if len(members) == 0:
                    print("Please retype as you cannot create a group with only yourself.")
                    continue
            data = json.dumps({'cmd': ['CREATEGROUP', group_name, username], 'args': members})
            client.send(data.encode())
        elif cmd == 'add':
            if len(rest.split()) < 2:
                print("Error: missing arguments.")
                continue
            group_name, new_members = rest.split(' ', 1)
            new_members = new_members.split()
            if username in new_members:
                new_members.remove(username)
            data = json.dumps({'cmd': ['GROUPMAN', 'ADD', group_name], 'args': new_members})
            client.send(data.encode())
        elif cmd == 'remove':
            if len(rest.split()) < 2:
                print("Error: missing arguments.")
                continue
            group_name, remove_members = rest.split(' ', 1)
            remove_members = remove_members.split()
            data = json.dumps({'cmd': ['GROUPMAN', 'REMOVE', group_name], 'args': remove_members})
            client.send(data.encode())
        elif cmd == 'remove':
            pass


def receive():
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
        exit
    while True:
        try:
            data = client.recv(2048).decode()
            print(data)
            data_loaded = json.loads(data)
            cmd = data_loaded['cmd']
            if cmd[0] == 'NEWUSER':
                print(f"System: {data_loaded['args']} has joined the chat!")
            elif cmd[0] == 'NEWMSG':
                sender = cmd[1]
                timestamp = cmd[2]
                print(f"{str(sender)} [{timestamp}]: {data_loaded['args']}")
            elif cmd[0] == 'ERROR':
                print(f"ERROR: {data_loaded['args']}")
            elif cmd[0] == 'OFFLINEMSG':
                print(
                    f"\n\***** ALERT: {cmd[1]} is offline right now. His/her last online time is {cmd[2]}. The message will be sent again once he/she is online. *****/\n")
            elif cmd[0] == 'CACHEDMSG':
                # CACHEDMSG i sender timestamp msg
                cached_messages = data_loaded['args']
                print("\nYou have the following buffered message when you're offline:\n")
                for cached_message in cached_messages:
                    sender = cached_message[1]
                    timestamp = cached_message[2]
                    print(f"|{cached_message[0]}th message| {str(sender)} [{timestamp}]: {cached_message[3]}")
            elif cmd[0] == 'CACHEDGPMSG':
                cached_messages = data_loaded['args']
                print("\nYou have the following buffered group message when you're offline:\n")
                for cached_message in cached_messages:
                    gp_name = cached_message[1]
                    sender = cached_message[2]
                    timestamp = cached_message[3]
                    print(
                        f"|{cached_message[0]}th message| |{gp_name}| {str(sender)} [{timestamp}]: {cached_message[3]}")
            elif cmd[0] == 'NEWGPMSG':
                gp_name = cmd[1]
                sender = cmd[2]
                timestamp = cmd[3]
                print(f"|{gp_name}| {sender} [{timestamp}]: {data_loaded['args']}")
            elif cmd[0] == 'OFFLINEGPMSG':
                print(
                    f"\n\***** ALERT: {cmd[2]} in {cmd[1]} is offline right now. His/her last online time is {cmd[3]}. The message will be sent again once he/she is online. *****/\n")
            elif cmd[0] == 'QUIT':
                client.close()
                exit(0)
            elif cmd[0] == 'BROADCAST':
                print(data_loaded['args'])
        except Exception as msg:
            print("Error occured. Closing connection now....")
            print(msg)
            print(data_loaded)
            client.close()
            exit(0)


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--ipv", help="IP version")
args = parser.parse_args()

port = 0
if args.ipv == "4":
    client = socket.socket()
elif args.ipv == "6":
    client = socket.socket(family=socket.AF_INET6)
else:
    print("Wrong IP Version!")
    exit(0)

username = input("Enter your username (it must have no spaces!): ")

while True:
    host = input("Enter host IP address: ")
    port = input("Enter host port")

    try:
        client.connect((host, port))
        break
    except socket.error as msg:
        print(f"Error: {msg}\n")

receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()
