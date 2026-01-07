import os
import json
import time
import hashlib
import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://cgoqgmxhqhunmcdaixvd.supabase.co"
SUPABASE_KEY = "sb_secret_RdTvzm5lAta74JArLSHrNQ_eimbOX-V"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PORT = int(os.environ.get("PORT", "10000"))
SERVER_TICK = 30

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAYERS = {}   # pseudo -> player data
CLIENTS = {}   # pseudo -> websocket
LOCK = asyncio.Lock()
SAVE_DIR = "players"
DATA_DIR = "data"

# add dev credentials (hashed) and patches list
DEV_CREDENTIALS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "dev": hashlib.sha256("dev123".encode()).hexdigest()
}
PATCHES = []

SERVER_START_TIME = time.time()

# Stocker les positions actuelles pour les HTTP requests
PLAYER_POSITIONS = {}  # pseudo -> {x, y, z}

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
            # build players map
            players_map = {
                p: {
                    "x": PLAYERS[p]["x"],
                    "y": PLAYERS[p]["y"],
                    "z": PLAYERS[p]["z"]
                }
                for p in PLAYERS
            }
            # status
            uptime = int(time.time() - SERVER_START_TIME)
            status = {
                "uptime": uptime,
                "players_online": len(CLIENTS),
                "total_players": len(PLAYERS)
            }
            payload = {
                "type": "update",
                "data": {
                    "players": players_map,
                    "status": status,
                    "patches": PATCHES
                }
            }

        msg = json.dumps(payload)

        remove = []
        for pseudo, ws in list(CLIENTS.items()):
            try:
                await ws.send_text(msg)
            except Exception:
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
    res = supabase.table("players").select("pseudo").limit(1).execute()
    print("[SUPABASE TEST]", res.data)



# ---- new HTTP API: auth, patch management ----

@app.post("/api/auth")
async def api_auth(req: Request):
    """
    Body JSON: { pseudo, password, register (bool) }
    Returns: { auth: "OK" | error, role: "dev"|"player" }
    """
    data = await req.json()
    pseudo = data.get("pseudo")
    password = data.get("password", "")
    register = bool(data.get("register", False))

    if not pseudo:
        return {"auth": "NO_PSEUDO"}

    # dev login
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if pseudo in DEV_CREDENTIALS:
        if DEV_CREDENTIALS[pseudo] == pw_hash:
            return {"auth": "OK", "role": "dev"}
        else:
            return {"auth": "BADPW"}

    # player login/register
    async with LOCK:
        if register:
            if pseudo in PLAYERS:
                return {"auth": "EXISTS"}
            PLAYERS[pseudo] = {
                "password": hashlib.sha256(password.encode()).hexdigest(),
                "x": 0, "y": 1, "z": 0,
                "pv": 100,
                "mana": 50,
                "endu": 80,
                "inventory": []
            }
            save_player_to_data(pseudo)
            save_player(pseudo)
            return {"auth": "OK", "role": "player"}
        else:
            if pseudo not in PLAYERS:
                return {"auth": "NOUSER"}
            if PLAYERS[pseudo]["password"] != hashlib.sha256(password.encode()).hexdigest():
                return {"auth": "BADPW"}
            return {"auth": "OK", "role": "player"}

@app.post("/api/patch")
async def api_post_patch(req: Request):
    """
    Body JSON: { version, title, description, type, author }
    Requires: dev auth (simple header Authorization: Basic dev:pw or include author who must be a dev)
    For simplicity: accepts requests where author matches a dev pseudo known in DEV_CREDENTIALS.
    """
    data = await req.json()
    author = data.get("author")
    if not author or author not in DEV_CREDENTIALS:
        return {"ok": False, "error": "unauthorized"}

    patch = {
        "version": data.get("version"),
        "title": data.get("title"),
        "description": data.get("description"),
        "type": data.get("type"),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "author": author
    }
    async with LOCK:
        PATCHES.insert(0, patch)
        # persist patches to disk
        try:
            with open(os.path.join(DATA_DIR, "patches.json"), "w", encoding="utf-8") as f:
                json.dump(PATCHES, f, ensure_ascii=False, indent=2)
        except:
            pass
    return {"ok": True, "patch": patch}

@app.get("/api/patches")
async def api_get_patches():
    # load from disk if exists
    try:
        with open(os.path.join(DATA_DIR, "patches.json"), "r", encoding="utf-8") as f:
            p = json.load(f)
            return {"patches": p}
    except:
        return {"patches": PATCHES}


@app.post("/api/player/position")
async def update_player_position(req: Request):
    """Reçoit la position du joueur via HTTP"""
    data = await req.json()
    pseudo = data.get("pseudo")
    
    if pseudo and pseudo in PLAYERS:
        async with LOCK:
            PLAYERS[pseudo]["x"] = data.get("x", PLAYERS[pseudo]["x"])
            PLAYERS[pseudo]["y"] = data.get("y", PLAYERS[pseudo]["y"])
            PLAYERS[pseudo]["z"] = data.get("z", PLAYERS[pseudo]["z"])
            
            PLAYER_POSITIONS[pseudo] = {
                "x": PLAYERS[pseudo]["x"],
                "y": PLAYERS[pseudo]["y"],
                "z": PLAYERS[pseudo]["z"]
            }
            
            save_player(pseudo)
            save_player_to_data(pseudo)
    
    return {"ok": True}

@app.post("/api/projectile")
async def handle_projectile(req: Request):
    """Reçoit un projectile et teste les collisions"""
    data = await req.json()
    pseudo = data.get("pseudo")
    x = data.get("x", 0)
    z = data.get("z", 0)
    damage = data.get("damage", 20)
    
    # Tester les collisions avec les ennemis
    # (À implémenter selon la logique du jeu)
    
    return {"ok": True}

@app.get("/api/players/positions")
async def get_all_positions():
    """Retourne les positions de tous les joueurs"""
    with lock:
        return {"positions": PLAYER_POSITIONS}


# new: chunk configuration
CHUNK_SIZE = 50  # units per chunk (must match client)
MAX_ROCKS_PER_CHUNK = 6
MAX_TREES_PER_CHUNK = 5
MAX_HOUSES_PER_CHUNK = 1
MAX_ENEMIES_PER_CHUNK = 3


@app.get("/api/chunks")
async def api_get_chunks(cx: int, cz: int, r: int = 1):
    """
    Retourne les chunks dans un rayon r autour du chunk (cx, cz).
    Query params: cx (int), cz (int), r (int)
    Response: { "chunks": { "<cx>,<cz>": [ {type,x,y,z,scale,...}, ... ], ... } }
    """
    result = {}
    for ci in range(cx - r, cx + r + 1):
        for cj in range(cz - r, cz + r + 1):
            key = f"{ci},{cj}"
            # deterministic RNG per chunk
            seed = (ci & 0xffffffff) << 32 ^ (cj & 0xffffffff)
            rng = random.Random(seed)
            objs = []
            # rocks
            for _ in range(rng.randint(0, MAX_ROCKS_PER_CHUNK)):
                local_x = rng.uniform(0, CHUNK_SIZE)
                local_z = rng.uniform(0, CHUNK_SIZE)
                world_x = ci * CHUNK_SIZE + local_x
                world_z = cj * CHUNK_SIZE + local_z
                scale = rng.uniform(0.8, 3.0)
                objs.append({"type": "Rock", "x": world_x, "y": 0, "z": world_z, "scale": scale})
            # trees
            for _ in range(rng.randint(0, MAX_TREES_PER_CHUNK)):
                local_x = rng.uniform(0, CHUNK_SIZE)
                local_z = rng.uniform(0, CHUNK_SIZE)
                world_x = ci * CHUNK_SIZE + local_x
                world_z = cj * CHUNK_SIZE + local_z
                trunk_h = rng.uniform(2, 4)
                trunk_r = rng.uniform(0.2, 0.6)
                leaf_r = rng.uniform(1.0, 2.5)
                fruit_count = rng.randint(0, 3)
                objs.append({
                    "type": "Tree",
                    "x": world_x, "y": 0, "z": world_z,
                    "trunk_height": trunk_h, "trunk_radius": trunk_r,
                    "leaf_radius": leaf_r, "fruit_count": fruit_count
                })
            # houses (rare)
            if rng.random() < 0.08:
                local_x = rng.uniform(0, CHUNK_SIZE)
                local_z = rng.uniform(0, CHUNK_SIZE)
                world_x = ci * CHUNK_SIZE + local_x
                world_z = cj * CHUNK_SIZE + local_z
                objs.append({"type": "House", "x": world_x, "y": 0, "z": world_z})
            # enemies
            for _ in range(rng.randint(0, MAX_ENEMIES_PER_CHUNK)):
                if rng.random() < 0.4:
                    local_x = rng.uniform(0, CHUNK_SIZE)
                    local_z = rng.uniform(0, CHUNK_SIZE)
                    world_x = ci * CHUNK_SIZE + local_x
                    world_z = cj * CHUNK_SIZE + local_z
                    speed = rng.uniform(1.0, 3.0)
                    damage = rng.uniform(3, 10)
                    hp = rng.uniform(50, 120)
                    objs.append({"type": "Enemy", "x": world_x, "y": 1, "z": world_z,
                                 "speed": speed, "damage": damage, "hp": hp})
            result[key] = objs
    return {"chunks": result}


# Route pour servir le dashboard HTML
@app.get("/")
async def serve_root():
    """Serve le dashboard principal"""
    if os.path.exists("site_web_realtime.html"):
        return FileResponse("site_web_realtime.html", media_type="text/html")
    else:
        return {"message": "Dashboard non trouvé. Lancez update_site.py pour le générer."}

@app.get("/dashboard")
async def serve_dashboard():
    """Alias pour /"""
    return await serve_root()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "online",
        "uptime": int(time.time() - SERVER_START_TIME),
        "players_online": len(CLIENTS),
        "total_players": len(PLAYERS)
    }


# --------------------------
# START FASTAPI UVICORN
# --------------------------
if __name__ == "__main__":
    print(f"\n🎮 Serveur MMO en ligne")
    print(f"📊 Dashboard: http://localhost:{PORT}/")
    print(f"🔌 WebSocket: wss://beta-game-w99g.onrender.com/ws")
    print(f"❤️ Health: http://localhost:{PORT}/health\n")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, ws="websockets")
