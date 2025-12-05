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
    print(f"[*] WebSocket server listening on port {PORT}")
    asyncio.create_task(broadcast_loop())


# --------------------------
# START FASTAPI UVICORN
# --------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT)
