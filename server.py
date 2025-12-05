import os
import json
import time
import hashlib
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

PORT = int(os.environ.get("PORT", "10000"))
SERVER_TICK = 30

app = FastAPI()

PLAYERS = {}   # pseudo -> player data
CLIENTS = {}   # pseudo -> websocket
LOCK = asyncio.Lock()
SAVE_DIR = "players"
DATA_DIR = "data"

def ensure_save_folder():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

def player_file(pseudo):
    return os.path.join(SAVE_DIR, f"{pseudo}.txt")

def save_player(pseudo):
    ensure_save_folder()
    try:
        with open(player_file(pseudo), "w", encoding="utf-8") as f:
            json.dump(PLAYERS[pseudo], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("[SAVE ERROR]", e)

def load_players():
    ensure_save_folder()
    global PLAYERS

    for fname in os.listdir(SAVE_DIR):
        if fname.endswith(".txt"):
            pseudo = fname.replace(".txt", "")
            try:
                with open(player_file(pseudo), "r", encoding="utf-8") as f:
                    PLAYERS[pseudo] = json.load(f)
            except:
                pass

def ensure_data_folder():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def player_file_path(pseudo):
    return os.path.join(DATA_DIR, f"{pseudo}.txt")

def save_player_to_data(pseudo):
    ensure_data_folder()
    try:
        with open(player_file_path(pseudo), "w", encoding="utf-8") as f:
            json.dump(PLAYERS[pseudo], f, indent=2)
    except Exception as e:
        print("Save DATA error:", e)

def load_players_from_data():
    ensure_data_folder()
    for file in os.listdir(DATA_DIR):
        if file.endswith(".txt"):
            pseudo = file[:-4]
            try:
                with open(player_file_path(pseudo), "r", encoding="utf-8") as f:
                    PLAYERS[pseudo] = json.load(f)
            except:
                print("Load DATA error:", file)



def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    pseudo = None

    # ----------------------
    # AUTH PART
    # ----------------------
    try:
        raw = await ws.receive_text()
        login = json.loads(raw)

        pseudo = login["pseudo"]
        password = login["password"]
        register = login["register"]

        async with LOCK:
            if register:
                if pseudo in PLAYERS:
                    await ws.send_text(json.dumps({"auth": "EXISTS"}))
                    await ws.close()
                    return

                PLAYERS[pseudo] = {
                    "password": hash_pw(password),
                    "x": 0, "y": 1, "z": 0,
                    "pv": 100,
                    "mana": 50,
                    "endu": 80,
                    "inventory": []
                }
                save_player_to_data(pseudo)
                save_player(pseudo)
                await ws.send_text(json.dumps({"auth": "OK"}))

            else:
                if pseudo not in PLAYERS:
                    await ws.send_text(json.dumps({"auth": "NOUSER"}))
                    await ws.close()
                    return

                if PLAYERS[pseudo]["password"] != hash_pw(password):
                    await ws.send_text(json.dumps({"auth": "BADPW"}))
                    await ws.close()
                    return

                await ws.send_text(json.dumps({"auth": "OK"}))
            CLIENTS[pseudo] = ws
            print(f"[+] {pseudo} connecté")

    except Exception as e:
        print("Auth error:", e)
        await ws.close()
        return

    # ----------------------
    # RECEIVE LOOP
    # ----------------------
    try:
        while True:
            data = await ws.receive_text()
            try:
                packet = json.loads(data)
            except:
                continue

            async with LOCK:
                PLAYERS[pseudo]["x"] = packet.get("x", PLAYERS[pseudo]["x"])
                PLAYERS[pseudo]["y"] = packet.get("y", PLAYERS[pseudo]["y"])
                PLAYERS[pseudo]["z"] = packet.get("z", PLAYERS[pseudo]["z"])
                save_player(pseudo)
                save_player_to_data(pseudo)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("Recv error:", e)

    # ----------------------
    # DISCONNECT CLEANUP
    # ----------------------
    async with LOCK:
        if pseudo in CLIENTS:
            del CLIENTS[pseudo]
        print(f"[-] {pseudo} déconnecté")


# --------------------------
# BROADCAST LOOP
# --------------------------
async def broadcast_loop():
    while True:
        await asyncio.sleep(1 / SERVER_TICK)

        async with LOCK:
            data = {
                "players": {
                    p: {
                        "x": PLAYERS[p]["x"],
                        "y": PLAYERS[p]["y"],
                        "z": PLAYERS[p]["z"]
                    }
                    for p in PLAYERS
                }
            }

        msg = json.dumps(data)

        remove = []
        for pseudo, ws in CLIENTS.items():
            try:
                await ws.send_text(msg)
            except:
                remove.append(pseudo)

        async with LOCK:
            for p in remove:
                if p in CLIENTS:
                    del CLIENTS[p]


@app.on_event("startup")
async def startup_event():
    load_players_from_data()
    load_players()
    print(f"[*] WebSocket server listening on port {PORT}")
    asyncio.create_task(broadcast_loop())


# --------------------------
# START FASTAPI UVICORN
# --------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, ws="websockets")
