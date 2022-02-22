import socket
import threading
import json
from datetime import datetime


def broadcast(msg):
    clients_lock.acquire()
    for broad_client in clients.values():
        broad_client.send(msg.encode())
    clients_lock.release()


def handle(client, name, groups_lock, clients_lock):
    global groups
    while True:
        try:
            data = client.recv(2048)
            clients_lastonline[name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_loaded = json.loads(data.decode())
            log(name, f"Recevied following data: {data_loaded}")
            cmd = data_loaded['cmd']
            if cmd[0] == 'SENDMSG':
                receiver = cmd[1]
                clients_lock.acquire()
                groups_lock.acquire()
                if receiver in groups and name in groups[receiver]['members']:
                    for member in groups[receiver]['members']:
                        if member == name:
                            continue
                        try:
                            data = json.dumps(
                                {'cmd': ['NEWGPMSG', receiver, name, cmd[2]], 'args': data_loaded['args']})
                            clients[member].send(data.encode())
                        except:
                            log(name, f"{receiver} unable to receive message. Cached.")
                            data = json.dumps({'cmd': ['OFFLINEGPMSG', receiver, member, clients_lastonline[member]],
                                               'args': data_loaded['args']})
                            client.send(data.encode())
                            data_loaded['cmd'].insert(2, name)
                            gp_cache.setdefault(member, []).append(data_loaded)
                elif receiver not in clients and receiver not in clients_lastonline:
                    log(name, f"Tried to send message to {receiver} but it doesn't exist.")
                    data = json.dumps({'cmd': ["ERROR"], 'args': f"Recevier {receiver} doesn't exist."})
                    client.send(data.encode())
                else:
                    try:
                        data = json.dumps({'cmd': ['NEWMSG', name, cmd[2]], 'args': data_loaded['args']})
                        clients[receiver].send(data.encode())
                    except:
                        log(name, f"{receiver} unable to receive message. Cached.")
                        data = json.dumps({'cmd': ['OFFLINEMSG', receiver, clients_lastonline[receiver]],
                                           'args': data_loaded['args']})
                        client.send(data.encode())
                        data_loaded['cmd'][1] = name
                        cache.setdefault(receiver, []).append(data_loaded)
                groups_lock.release()
                clients_lock.release()
            elif cmd[0] == 'CREATEGROUP':
                group_name = cmd[1]
                admin = cmd[2]
                members = data_loaded['args']
                groups_lock.acquire()
                if group_name in groups:
                    log(name, f"Group '{group_name}' already exists.")
                    data = json.dumps({'cmd': ["ERROR"],
                                       'args': f"Group '{group_name}' already exists. Please pick a new group name."})
                    client.send(data.encode())
                else:
                    all_exist = True
                    clients_lock.acquire()
                    for member in members:
                        if member not in clients and member not in clients_lastonline:
                            log(name, f"Tried to add {receiver} user to group {group_name} but the user doesn't exist.")
                            data = json.dumps(
                                {'cmd': ["ERROR"], 'args': f"User {receiver} doesn't exist. Please retry"})
                            client.send(data.encode())
                            all_exist = False

                    if all_exist:
                        members.append(admin)
                        groups[group_name] = {'admin': admin, 'members': members}
                        for member in members:
                            if member != name:
                                data = json.dumps(
                                    {'cmd': ["BROADCAST"],
                                     'args': f"You have been added to group '{group_name}' with members of {members}."})
                                clients[member].send(data.encode())
                            else:
                                data = json.dumps(
                                    {'cmd': ["BROADCAST"],
                                     'args': f"You have created group '{group_name}' with members of {members}."})
                                client.send(data.encode())
                    clients_lock.release()
                print(f"Current group list: {groups}")
                groups_lock.release()
            elif cmd[0] == 'GROUPMAN':
                group_name = cmd[2]
                groups_lock.acquire()
                if group_name not in groups:
                    data = json.dumps(
                        {'cmd': ["ERROR"], 'args': f"'{group_name}' group doesn't exist."})
                    client.send(data.encode())
                elif groups[group_name]['admin'] == name:
                    if cmd[1] == 'ADD':
                        members_list = data_loaded['args']
                        for member in members_list:
                            if member not in groups[group_name]['members']:
                                groups[group_name]['members'].append(member)
                        clients_lock.acquire()
                        for member in groups[group_name]['members']:
                            data = json.dumps(
                                {'cmd': ["BROADCAST"],
                                 'args': f"Group '{group_name}' has been updated with new member list: {members}."})
                            clients[member].send(data.encode())
                        clients_lock.release()
                    elif cmd[1] == 'REMOVE':
                        members_list = data_loaded['args']
                        for member in members_list:
                            if member in groups[group_name]['members']:
                                groups[group_name]['members'].remove(member)
                                data = json.dumps(
                                    {'cmd': ["BROADCAST"],
                                     'args': f"You have been removed from group '{group_name}'."})
                                clients[member].send(data.encode())
                        clients_lock.acquire()
                        for member in groups[group_name]['members']:
                            data = json.dumps(
                                {'cmd': ["BROADCAST"],
                                 'args': f"Group '{group_name}' has been updated with new member list: {members}."})
                            clients[member].send(data.encode())
                        clients_lock.release()
                else:
                    data = json.dumps(
                        {'cmd': ["ERROR"], 'args': f"You are not the admin of '{group_name}'."})
                    client.send(data.encode())
                groups_lock.release()
            elif cmd[0] == 'QUIT':
                clients_lock.acquire()
                del clients[name]
                clients_lock.release()
                broadcast(json.dumps({'cmd': ['BROADCAST'], 'args': f"{name} has left the chat."}))
                data = json.dumps({'cmd': ['QUIT']})
                client.send(data.encode())
                exit(0)
            else:
                data = json.dumps(
                    {'cmd': ["ERROR"], 'args': "Invalid command."})
                client.send(data.encode())


        except Exception as msg:
            # broadcast missing of client
            clients_lock.acquire()
            if name in clients:
                del clients[name]
            clients_lock.release()
            broadcast(json.dumps({'cmd': ['ERROR'], 'args': f"{name}'s client occured an error."}))
            print("Error occured. Closing connection now....")
            print(msg)
            client.close()
            exit(0)


def log(addr, msg):
    print(f"{str(addr)}: {msg}")


def setup(socket):
    global clients
    while True:
        client, addr = socket.accept()
        print(f"Connected with {str(addr)}")

        cmd = json.dumps({'cmd': ['NICK'], 'args': ''})
        client.send(cmd.encode())

        data = client.recv(2048).decode()
        name = json.loads(data)
        if name['cmd'][0] == 'NAME':
            clients_lock.acquire()
            clients[name['args']] = client
            clients_lastonline[name['args']] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clients_lock.release()
            log(addr, f"Setup its nickname as {name['args']}")
            broadcast(json.dumps({'cmd': ['NEWUSER'], 'args': name['args']}))

            if name['args'] in cache and len(cache[name['args']]) > 0:
                log(name['args'], "Found cached message. Re-sending right now....")
                i = 1
                cache_to_sent = []
                for cached_data in cache[name['args']]:
                    log(name['args'], f"Sorting {str(i)}th cached message...")
                    cached_data_cmd = cached_data['cmd']
                    cache_to_sent.append([i, cached_data_cmd[1], cached_data_cmd[2], cached_data['args']])
                    i += 1
                data = json.dumps({'cmd': ['CACHEDMSG'], 'args': cache_to_sent})
                log(name['args'], f"Sending following cached data: {data}")
                client.send(data.encode())
                cache[name['args']] = []

            if name['args'] in gp_cache and len(gp_cache[name['args']]) > 0:
                log(name['args'], "Found cached group message. Re-sending right now....")
                i = 1
                cache_to_sent = []
                for cached_data in gp_cache[name['args']]:
                    log(name['args'], f"Sorting {str(i)}th cached group message...")
                    cached_data_cmd = cached_data['cmd']
                    cache_to_sent.append(
                        [i, cached_data_cmd[1], cached_data_cmd[2], cached_data_cmd[3], cached_data['args']])
                    i += 1
                data = json.dumps({'cmd': ['CACHEDGPMSG'], 'args': cache_to_sent})
                log(name['args'], f"Sending following cached group data: {data}")
                client.send(data.encode())
                gp_cache[name['args']] = []

            # Start Handling Thread For Client
            thread = threading.Thread(target=handle, args=(client, name['args'], groups_lock, clients_lock))
            thread.start()
        else:
            print(f"Error establishing username with {str(addr)}.")
            print(f"Terminated connection with {str(addr)}.")
            client.close()
            exit


s4 = socket.socket()
s6 = socket.socket(family=socket.AF_INET6)

host4 = socket.gethostname()
host6 = socket.gethostname()
port4 = 59363
port6 = 59364
print(f"IPv4: {str(socket.gethostbyname(host4))}:{port4}")
print(f"IPv6: {str(socket.getaddrinfo(host6, port6, family=socket.AF_INET6)[0][4][0])}")

s4.bind((host4, port4))
s4.listen(5)

host6 = socket.getaddrinfo(host6, port6, family=socket.AF_INET6)[0][4][0]
s6.bind((host6, port6))
s6.listen(5)

groups = {}
groups_lock = threading.Lock()
clients_lock = threading.Lock()

clients = {}
clients_lastonline = {}
cache = {}
gp_cache = {}

thread = threading.Thread(target=setup, args=(s4,))
thread.start()

thread = threading.Thread(target=setup, args=(s6,))
thread.start()
