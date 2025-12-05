
import socket
import threading
import json
import hashlib
import os
import time

PORT = int(os.environ.get("PORT", "10000"))
SERVER_TICK = 30

PLAYERS = {}
CLIENTS = {}
LOCK = threading.Lock()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def handle_client(conn):
    global PLAYERS, CLIENTS

    try:
        raw = conn.recv(4096).decode()
        login = json.loads(raw)

        pseudo = login["pseudo"]
        password = login["password"]
        register = login["register"]

        if register:
            if pseudo in PLAYERS:
                conn.send(json.dumps({"auth": "EXISTS"}).encode())
                conn.close()
                return

            PLAYERS[pseudo] = {
                "password": hash_pw(password),
                "x": 0, "y": 1, "z": 0,
                "pv": 100, "mana": 50, "endu": 80,
                "inventory": []
            }
            conn.send(json.dumps({"auth": "OK"}).encode())

        else:
            if pseudo not in PLAYERS:
                conn.send(json.dumps({"auth": "NOUSER"}).encode())
                conn.close()
                return

            if PLAYERS[pseudo]["password"] != hash_pw(password):
                conn.send(json.dumps({"auth": "BADPW"}).encode())
                conn.close()
                return

            conn.send(json.dumps({"auth": "OK"}).encode())

    except Exception as e:
        print("Auth error:", e)
        conn.close()
        return

    CLIENTS[conn] = pseudo
    print(f"[+] {pseudo} connecté")

    buffer = ""
    try:
        while True:
            chunk = conn.recv(4096).decode()
            if not chunk:
                break

            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                try:
                    packet = json.loads(line)
                except:
                    continue

                with LOCK:
                    PLAYERS[pseudo]["x"] = packet.get("x", PLAYERS[pseudo]["x"])
                    PLAYERS[pseudo]["y"] = packet.get("y", PLAYERS[pseudo]["y"])
                    PLAYERS[pseudo]["z"] = packet.get("z", PLAYERS[pseudo]["z"])

    except:
        pass

    print(f"[-] {pseudo} déconnecté")
    del CLIENTS[conn]
    conn.close()

def broadcast_loop():
    while True:
        with LOCK:
            data = {
                "players": {
                    p: {"x": PLAYERS[p]["x"], "y": PLAYERS[p]["y"], "z": PLAYERS[p]["z"]}
                    for p in PLAYERS
                }
            }

        msg = (json.dumps(data) + "\n").encode()

        for conn in list(CLIENTS.keys()):
            try:
                conn.sendall(msg)
            except:
                pass

        time.sleep(1 / SERVER_TICK)

def start():
    print("[*] Render server online on port", PORT)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", PORT))
    s.listen()

    threading.Thread(target=broadcast_loop, daemon=True).start()

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

start()
