import socket
import threading
import json
from datetime import datetime


def broadcast(msg):
    for client in clients.items():
        client.send(msg)


def handle(client, name, groups_lock, clients_lock):
    global groups
    while True:
        try:
            data = client.recv(2048).decode()
            data_loaded = json.loads(data)
            log(name, f"Recevied following data: {data_loaded}")
            cmd = data_loaded['cmd']
            if cmd[0] == 'SENDMSG':
                receiver = cmd[1]
                clients_lock.acquire()
                if receiver not in clients:
                    log(name, f"Tried to send message to {receiver} but it doesn't exist.")
                    data = json.dumps({'cmd':["ERROR"], 'args':f"Recevier {receiver} doesn't exist."})
                    client.send(data.encode())
                else:
                    try:
                        data = json.dumps({'cmd':['NEWMSG',name, cmd[1]], 'args': data_loaded['args']})
                        clients[receiver].send(data.encode())
                    except:
                        log(name, f"{receiver} unable to receive message. Cached.")
                        data = json.dumps({'cmd':['OFFLINEMSG', receiver], 'args': data_loaded['args']})
                        client.send(data.encode())
                clients_lock.release()

        except:
            print("Error occured. Closing connection now....")
            client.close()
            return

def log(addr, msg):
    print(f"{str(addr)}: {msg}")


s = socket.socket()
host = socket.gethostname()
port = 12345
print(f"IP: {str(socket.gethostbyname(host))}")

s.bind((host, port))
s.listen()

groups = {}
groups_lock = threading.Lock()
clients_lock = threading.Lock()

clients = {}
cache = {}

while True:
    client, addr = s.accept()
    print(f"Connected with {str(addr)}")

    cmd = json.dumps({'cmd': ['NICK'], 'args': ''})
    client.send(cmd.encode())

    data = client.recv(2048).decode()
    name = json.loads(data)
    if name['cmd'][0] == 'NAME':
        clients_lock.acquire()
        clients[name['args']] = client
        clients_lock.release()
        log(addr, f"Setup its nickname as {name['args']}")
        if name['args'] in cache and len(name['args']) > 0:
            #                 Resend all cached message
            pass
        broadcast(json.dumps({'cmd': ['NEWUSER'], 'args': name['args']}).encode())

        # Start Handling Thread For Client
        thread = threading.Thread(target=handle, args=(client, name['args'], groups_lock, clients_lock))
        thread.start()
    else:
        print(f"Error establishing username with {str(addr)}.")
        print(f"Terminated connection with {str(addr)}.")
        client.close()