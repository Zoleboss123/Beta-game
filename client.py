import websocket
import threading
import json
import time

# --------------------------------------------------------------------
# CONFIG (Render = WSS obligatoire)
# --------------------------------------------------------------------
SERVER_IP = "beta-game-w99g.onrender.com"
SERVER_PORT = None                       # plus utilisé en WebSocket
WS_URL = "beta-game-w99g.onrender.com"

connected = False
server_data = {}
lock = threading.Lock()
my_pseudo = None

ws = None  # WebSocket client


# --------------------------------------------------------------------
# RECEVOIR LES DONNÉES DU SERVEUR (WebSocket)
# --------------------------------------------------------------------
def listen_server():
    global server_data, connected

    while connected:
        try:
            msg = ws.recv()   # REÇOIT TEXTE JSON
            if not msg:
                print("[!] Serveur fermé")
                break

            try:
                packet = json.loads(msg)
                with lock:
                    server_data = packet
            except json.JSONDecodeError:
                continue

        except Exception as e:
            print("[!] Erreur listen_server:", e)
            break

    connected = False
    print("[!] Déconnecté du serveur")


# --------------------------------------------------------------------
# CONNEXION / LOGIN VIA WEBSOCKET
# --------------------------------------------------------------------
def connect_to_server(pseudo, password, register=False):
    global connected, ws, my_pseudo, WS_URL

    # créer l'URL WebSocket
    WS_URL = f"wss://{SERVER_IP}/ws"

    print("Connexion à :", WS_URL)

    try:
        ws = websocket.WebSocket()
        ws.connect(WS_URL)  # -> wss://tonserveur/ws
        print("[OK] Connecté via WebSocket")
    except Exception as e:
        print("Erreur connexion WebSocket:", e)
        return False

    login = {
        "pseudo": pseudo,
        "password": password,
        "register": register
    }

    try:
        ws.send(json.dumps(login))
        reply = json.loads(ws.recv())
    except Exception as e:
        print("Erreur lors de l'authentification:", e)
        return False

    if reply.get("auth") != "OK":
        print("Erreur auth:", reply.get("auth"))
        return False

    print("[OK] Authentification réussie !")

    my_pseudo = pseudo
    connected = True

    threading.Thread(target=listen_server, daemon=True).start()
    return True


# --------------------------------------------------------------------
# ENVOYER POSITION / PROJETS
# --------------------------------------------------------------------
def send_player_state(x, y, z, projectile=None):
    if not connected:
        return

    packet = {"x": x, "y": y, "z": z}

    try:
        ws.send(json.dumps(packet))
    except:
        pass


def send_world_event(event: dict):
    if not connected:
        return

    packet = {"world_event": event}

    try:
        ws.send(json.dumps(packet))
    except:
        pass
