from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time
import math
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from tkinter.font import Font
import random
import os
import threading
import client



map_file_path = "world_map.txt"
if not os.path.exists(map_file_path):
    with open(map_file_path, 'w') as f:
        f.write('')  # Crée un fichier vide s'il n'existe pas

# demander l'IP et le port du serveur (utile pour jouer entre deux ordinateurs)
print("\n--- Configuration du serveur ---")
print("Exemples :")
print("  - Localhost : 127.0.0.1 port 5000")
print("  - Dev Tunnels (VS Code) : jbk67r05-5000.uks1.devtunnels.ms port 443")
print("  - Ngrok : X.tcp.ngrok.io port XXXXX")
print()

# Demande simplement l'adresse du serveur Render (pas de port)
server_ip = input("Adresse du serveur Render (ex: mmo-test.onrender.com) : ").strip()
if server_ip:
    client.SERVER_IP = server_ip  # WebSocket se connectera automatiquement à wss://SERVER_IP/ws


# ===== CONNEXION AU SERVEUR AVANT URSINA =====
connected = False
while not connected:
    print("\n--- Connexion au serveur ---")
    pseudo = input("Pseudo : ")
    password = input("Mot de passe : ")
    register_choice = input("Créer un compte ? (oui/non) : ").lower()
    
    register = register_choice == "oui"
    if register:
        print("(Mode : Création de compte)")
    else:
        print("(Mode : Connexion)")
    
    # Utilise le nouveau client WebSocket
    connected = client.connect_to_server(pseudo, password, register=register)

    if not connected:
        print("Connexion échouée. Veuillez réessayer.\n")

# ===== MAINTENANT ON CRÉE URSINA =====

class Starte():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jeu en 3D")
        self.root.attributes('-topmost', True)  # Au premier plan
        self.root.grab_set()  # Modal - bloque les autres fenêtres

        WIDTH, HEIGHT = 1200, 300

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack()
        self.titre = tk.Label(self.canvas, text="Jeu en 3D super cool !", font=("Arial", 120))
        self.titre.pack(pady=15)
        self.root.update()  # Force l'affichage immédiat
        time.sleep(5)
    def destroy_start(self):
        self.root.destroy()


def fetch_users_online_with_progress():
        global sarte
        progress_win = tk.Toplevel()
        progress_win.title("Chagement du jeu en cours...")
        progress_win.geometry("600x150")
        progress_win.attributes('-topmost', True)  # Au premier plan
        progress_win.grab_set()  # Modal
        label = tk.Label(progress_win, text="Téléchargement des rescources...", font=("Arial", 12))
        label.pack(pady=10)
        file_label = tk.Label(progress_win, text="", font=("Arial", 10))
        file_label.pack(pady=5)
        progress_var = tk.DoubleVar()
        progress_bar = tk.Scale(progress_win, variable=progress_var, orient="horizontal", length=350, from_=0, to=100, showvalue=0)
        progress_bar.pack(pady=10)
        percent_label = tk.Label(progress_win, text="0%")
        percent_label.pack()
        for loop in range(100):
            progress_var.set(loop)
            percent_label.config(text=f"{loop}%")
            progress_win.update()
            time.sleep(0.25)
        progress_win.destroy()
        
        sarte.destroy_start()




def distance_xz(a, b):
    """Distance en XZ entre deux positions (ignore Y)."""
    return math.hypot(a.x - b.x, a.z - b.z)


app = Ursina()

window.title = 'Jeu 3D RPG - Ramassage et Sorts'
window.borderless = False
window.fps_counter.enabled = False



# --- Monde ---
ground = Entity(model='plane', scale=1000, texture='grass', collider='box')
Sky(texture='sky_sunset')

# --- Joueur ---
player = FirstPersonController()
player.cursor.visible = True
player.speed = 20
player.gravity = 1



#--- Ennemi ---
class Enemy:
    def __init__(self, enemy_position_x, enemy_position_y, enemy_position_z, enemy_speed, enemy_damage, enemy_pv):
        # use Vec3 so Ursina entities get a proper vector position
        self.enemy_position = Vec3(enemy_position_x, enemy_position_y, enemy_position_z)
        self.enemy_parent = Entity(model='cube', color=color.clear, scale=(1,2,1), position=self.enemy_position, collider='box')
        self.enemy_model = Entity(model='cube', color=color.red, scale=(1,2,1), position=self.enemy_position, collider='box')
        self.enemy_speed = enemy_speed
        self.enemy_damage = enemy_damage
        self.enemy_pv = enemy_pv

list_enemy = []




# --- Stats du joueur ---
pv_max, mana_max, endu_max = 100, 50, 80
pv, mana, endu = pv_max, mana_max, endu_max

# --- Interface ---

pv_bar = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.5,0.04), position=(-0.35,0.45))
endu_bar = Entity(parent=camera.ui, model='quad', color=color.green, scale=(0.5,0.04), position=(-0.35,0.40))
mana_bar = Entity(parent=camera.ui, model='quad', color=color.azure, scale=(0.5,0.04), position=(-0.35,0.35))

pv_text_affichage = Text(parent=camera.ui, text=f'{int(pv)}/{pv_max}', position=(-0.3,0.45), scale=1.2)
endu_text_affichage = Text(parent=camera.ui, text=f'{int(endu)}/{endu_max}', position=(-0.3,0.40), scale=1.2)
mana_text_affichage = Text(parent=camera.ui, text=f'{int(mana)}/{mana_max}', position=(-0.3,0.35), scale=1.2)

# --- Dialogue box ---
dialogue_text = Text(parent=camera.ui, text='', origin=(0,0), scale=1.2, position=(0, -0.4), enabled=False)

def show_dialogue(text):
    dialogue_text.enabled = True
    dialogue_text.text = text
    invoke(lambda: setattr(dialogue_text,'enabled',False), delay=4)

# --- Inventaire ---
class Inventory():
    def __init__(self):
        self.invent_parent = Entity(
            parent=camera.ui, 
            model='quad', 
            color=color.rgba(0,0,0,150), 
            scale=(0.6,0.4), 
            position=(0,0), 
            enabled=False,
            z=0
        )
        self.items = []
    
    def item_places(self):
        places = []
        for i in range(8):
            for j in range(8):
                places.append((-0.25 + j*0.06, 0.15 - i*0.06))
        return places

    def add_item(self, item_name):
        if len(self.items) < 64:
            self.items.append(item_name)
            self.update_inventory()

    def update_inventory(self):
        for child in self.invent_parent.children:
            destroy(child)
        
        places = self.item_places()

        for index, item in enumerate(self.items):
            x, y = places[index]

            if item == 'Pomme':
                Entity(parent=self.invent_parent, model='sphere', color=color.red, scale=0.05, position=(x, y), z=-0.01)
                Text(parent=self.invent_parent, text='Pomme', scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))
            
            elif item == 'Gemme dorée':
                Entity(parent=self.invent_parent, model='cube', color=color.yellow, scale=0.05, position=(x, y), z=-0.01)
                Text(parent=self.invent_parent, text='Gemme',color=color.white, scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))
            elif item == 'Pioche':
                Entity(parent=self.invent_parent, model='cube', color=color.brown, scale=(0.05,0.02,0.02), position=(x, y), z=-0.01)
                Entity(parent=self.invent_parent, model='cube', color=color.gray, scale=(0.01,0.01,0.4), position=(x+0.015, y), z=-0.005)
                Text(parent=self.invent_parent, text='Pioche',color=color.white, scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))
            elif item == 'Roche':
                Entity(parent=self.invent_parent, model='cube', color=color.gray, scale=0.05, position=(x, y), z=-0.01)
                Text(parent=self.invent_parent, text='Roche',color=color.white, scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))
            elif item == 'Hache':
                Entity(parent=self.invent_parent, model='cube', color=color.brown, scale=(0.05,0.02,0.02), position=(x, y), z=-0.01)
                Entity(parent=self.invent_parent, model='cube', color=color.gray, scale=(0.02,0.02,0.03), position=(x+0.015, y+0.015), z=-0.005)
                Text(parent=self.invent_parent, text='Hache',color=color.white, scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))
            elif item == 'Bois':
                Entity(parent=self.invent_parent, model='cube', color=color.brown, scale=0.05, position=(x, y), z=-0.01)
                Text(parent=self.invent_parent, text='Bois',color=color.white, scale=0.04, position=(x, y+0.03), z=-0.02, origin=(0,0))

# --- Objets ramassables ---
apple = Entity(model='sphere', color=color.red, position=(3,0.5,3), collider='sphere')
gem = Entity(model='cube', color=color.yellow, position=(5,0.5,3), collider='box')
pickup_names = {apple:'Pomme', gem:'Gemme dorée'}

# --- NPC ---
npc = Entity(model='cube', color=color.azure, position=(0,0.5,6), collider='box')


class Rock(Entity):
    def __init__(self, position=(0,0,0), scale=1, **kwargs):
        super().__init__(
            parent=scene,
            model='cube',
            color=color.gray,
            scale=scale,
            position=position,
            collider='box',
            **kwargs
        )
        self.nombre_de_pierres = 20
# --- Spawn de rochers ---
rock = []

class HotBar:
    def __init__(self):
        # UI parent for hotbar
        self.parent = Entity(parent=camera.ui, model='quad', color=color.clear, scale=(0.42,0.11), position=(0,-0.4))
        self.slots = 10
        self.items = [None] * self.slots
        self.slot_entities = []
        for i in range(self.slots):
            slot = Entity(parent=self.parent, model='quad', color=color.dark_gray, scale=(0.2,0.2), position=(-1.25 + i*0.3, 1))
            self.slot_entities.append(slot)
            # slot number
            Text(parent=slot, text=str(i+1), scale=0.3, position=(0,-0.03), origin=(0,0))
        self.index = 0
        # set initial visual selection
        self.select_slot(self.index)

    def clear_slot(self, index):
         if 0 <= index < self.slots:
             self.items[index] = None
             # remove visuals
             for c in list(self.slot_entities[index].children):
                 destroy(c)
             Text(parent=self.slot_entities[index], text=str(index+1), scale=0.3, position=(0,-0.03), origin=(0,0))


    def add_item(self, item_name):
        for i in range(self.slots):
            if self.items[i] is None:
                self.items[i] = item_name
                if item_name == 'Pioche':
                    Entity(parent=self.slot_entities[i], model='cube', color=color.brown, scale=(0.2,0.08,0.08), position=(0,0), origin=(0,0))
                    Entity(parent=self.slot_entities[i], model='cube', color=color.gray, scale=(0.06,0.06,0.6), position=(0.03,0), origin=(0,0))
                elif item_name == 'Hache':
                    Entity(parent=self.slot_entities[i], model='cube', color=color.brown, scale=(0.2,0.08,0.08), position=(0,0), origin=(0,0))
                    Entity(parent=self.slot_entities[i], model='cube', color=color.gray, scale=(0.06,0.06,0.06), position=(0.03,0.015), origin=(0,0))
                 # minimal visual: add item name on the slot
                Text(parent=self.slot_entities[i], text=item_name, color=color.white, scale=0.035, position=(0,0), origin=(0,0))
                return True
        return False

    def select_slot(self, index):
        if 0 <= index < self.slots:
            # reset all slot visuals
            for i, slot in enumerate(self.slot_entities):
                slot.color = color.dark_gray
            # select the requested slot
            self.index = index
            self.slot_entities[index].color = color.azure
            
    def get_selected_item(self):
        return self.items[self.index]


AZERTY_HOTBAR_KEYS = {
    '&': 0, '2': 1, '"': 2, "'": 3, '(': 4,
    '-': 5, '7': 6, '_': 7, '9': 8, '0': 9
}

# create sl
class Pickaxe(Entity):
    def __init__(self, position=(0,0,0), **kwargs):
        super().__init__(parent=scene, model='cube', color=color.clear, scale=(2.5,1,0.5), position=position, collider='box', **kwargs)
        # simple child visuals for manche/tete
        self.manche = Entity(parent=self, model='cube', color=color.brown, scale=(0.08,0.9,0.08), position=(0,-0.15,0), collider='box')
        self.tete = Entity(parent=self, model='cube', color=color.gray, scale=(0.5,0.2,0.2), position=(0,0.15,0), collider='box')
        self.name = 'Pioche'
        # map_position helper (int tuple)
        self.map_position = (int(round(position[0])), int(round(position[1])), int(round(position[2])))

# --- Créer la pioche dans le monde et la hotbar ---
pickaxe_world = Pickaxe(position=(6,0.5,3))
pickup_names[pickaxe_world] = 'Pioche'

class Haxe(Entity):
    def __init__(self, position=(0,0,0), **kwargs):
        super().__init__(parent=scene, model='cube', color=color.clear, scale=(2.5,1,0.5), position=position, collider='box', **kwargs)
        # simple child visuals for manche/tete
        self.manche = Entity(parent=self, model='cube', color=color.brown, scale=(0.08,0.9,0.08), position=(0,-0.15,0), collider='box')
        self.tete = Entity(parent=self, model='cube', color=color.gray, scale=(0.25,0.2,0.2), position=(-0.125,0.25,0), collider='box')
        self.name = 'Hache'
        # map_position helper (int tuple)
        self.map_position = (int(round(position[0])), int(round(position[1])), int(round(position[2])))

haxe = Haxe(position=(-6,0.5,-2))
pickup_names[haxe] = 'Hache'

# Hotbar instance
hotbar = HotBar()

class Tree(Entity):
    def __init__(self, position=(0,0,0), trunk_height=3, trunk_radius=0.3, 
                 leaf_radius=1.5, fruit_count=3, **kwargs):
        super().__init__(position=position, **kwargs)

        # Tronc
        self.trunk = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            scale=(trunk_radius, trunk_height, trunk_radius),
            position=(0, trunk_height/2, 0),
            collider='box'  # toujours sur le sol
        )

        # Feuillage
        self.leaves = Entity(
            parent=self,
            model='sphere',
            color=color.green,
            scale=(leaf_radius, leaf_radius, leaf_radius),
            position=(0, trunk_height + leaf_radius/2, 0),
            collider='sphere'  # toujours sur le sol
        )

        # Fruits
        self.nombre_fruits = 2
        self.nombre_wood = 5
tree = []        

# --- Spawn d’arbres ---


class House():
    def __init__(self, position=( 10, 2.5, 10)):
        # Base
        self.base = Entity(model='cube', color=color.gray, scale=(6,5,6), position=position)
        
        # Murs : gauche, droite, arrière
        self.walls = [
            Entity(model='cube', color=color.gray, scale=(0.3,5,6), position=(position[0]-3,2.5,position[2])),  # gauche
            Entity(model='cube', color=color.gray, scale=(0.3,5,6), position=(position[0]+3,2.5,position[2])),  # droite
            Entity(model='cube', color=color.gray, scale=(6,5,0.3), position=(position[0],2.5,position[2]-3)),  # arrière
        ]
        # Mur avant : porte au centre
        self.front_wall_left = Entity(model='cube', color=color.gray, scale=(2.25,5,0.3), position=(position[0]-1.875,2.5,position[2]+3))
        self.front_wall_right = Entity(model='cube', color=color.gray, scale=(2.25,5,0.3), position=(position[0]+1.875,2.5,position[2]+3))
        
        # Porte
        self.door = Entity(parent=self.base, model='cube', color=color.dark_gray, scale=(0.5,1,0.02), collider='box', position=(0,0,0.5))
        self.door_open = False

    def toggle_door(self):
        if not self.door_open:
            self.door_open = True
            destroy(self.door)
            self.door = Entity(parent=self.base, model='cube', color=color.dark_gray, scale=(0.02,1,0.3), collider='box', position=(0.125,0,0.65))
            show_dialogue("Tu ouvres la porte de la maison.")
        else:
            destroy(self.door)
            self.door = Entity(parent=self.base, model='cube', color=color.dark_gray, scale=(0.5,1,0.02), collider='box', position=(0,0,0.5))
            self.door_open = False
            show_dialogue("Tu fermes la porte de la maison.")

# --- Créer la maison ---
house =[] 
# --- Sorts ---
spells = ['Boule de feu', 'Éclair', 'Soin']
current_spell = 0



projectiles = []

def shoot(color_choice):
    bullet = Entity(parent=camera, model='sphere', color=color_choice, scale=0.2, position=camera.position + Vec3(0,0,0), collider="box")
    bullet.world_parent = scene
    bullet.speed = 50
    bullet.damage = 50 if color_choice==color.red else 20
    # s'assurer que la direction du bullet est celle de la caméra au moment du tir
    projectiles.append(bullet)
    return projectiles



def cast_spell():
    global current_spell, mana
    if spells[current_spell] == 'Boule de feu':
        if mana >= 5:
            mana_cost = 5
            mana -= mana_cost
            shoot(color.red)
    elif spells[current_spell] == 'Éclair':
        if mana >= 20:    
            mana_cost = 20
            mana -= mana_cost
            shoot(color.yellow)
    elif spells[current_spell] == 'Soin':
        if mana >= 50:    
            mana_cost = 50
            mana -= mana_cost
            global pv
            pv = clamp(pv + 20, 0, pv_max)
            show_dialogue('Tu te soignes !')

door_open = False  # état de la porte

now_spell = Text(parent=camera.ui, text=f'Sort sélectionné : {spells[current_spell]}', position=(0.35, 0.40, 0.40))

inventory = Inventory()

if os.path.exists(map_file_path) and os.path.getsize(map_file_path) > 0:
    with open(map_file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split(',')
            if parts[0] == 'Rock':
                x, y, z, scale = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                rock.append(Rock(position=(x,y,z), scale=scale))
            elif parts[0] == 'Tree':
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                trunk_height, trunk_radius = float(parts[4]), float(parts[5])
                leaf_radius = float(parts[6])
                fruit_count = int(parts[7])
                tree.append(Tree(position=(x,y,z), trunk_height=trunk_height, trunk_radius=trunk_radius, leaf_radius=leaf_radius, fruit_count=fruit_count))
            elif parts[0] == 'House':
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                house.append(House(position=(x,y,z)))
            elif parts[0] == 'Enemy':
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                speed = float(parts[4])
                damage = float(parts[5])
                pv_enemy = float(parts[6])
                list_enemy.append(Enemy(x,y,z,speed,damage,pv_enemy))
else:
    with open(map_file_path, 'w') as f:
        f.write('')  # Crée un fichier vide s'il n'existe pas
    rock.append(Rock(position=(random.randint(-500, 500),0,random.randint(-500, 500)), scale=random.randint(1, 6)))
    for x in range(50):
        rock.append(Rock(position=(random.randint(-500, 500),0,random.randint(-500, 500)), scale=random.randint(1, 6)))
    tree.append(Tree(position=(2,0,2)))
    for x in range(200):
        tree.append(Tree(position=(random.randint(-500, 500), 0 , random.randint(-500, 500)), trunk_height=random.randint(2, 4),trunk_radius=((random.randint(2, 5))/10), leaf_radius=random.randint(1, 10)))
    for x in range(30):
        list_enemy.append(Enemy(random.randint(-500, 500),1,random.randint(-500, 500),2,5,100))
    house.append(House(position=(10,2.5,10)))
    for x in range(20):
        house.append(House(position=(random.randint(-500, 500),2.5,random.randint(-500, 500))))

def save_world():
    with open(map_file_path, 'w') as f:
        f.write('')  # Vide le fichier avant d'écrire

        # Rocks
        for r in list(rock):
            try:
                f.write(f'Rock,{r.position.x},{r.position.y},{r.position.z},{r.scale.x}\n')
            except Exception:
                # entité détruite ou invalide -> ignorer
                continue

        # Trees
        for t in list(tree):
            try:
                # accéder aux sous-éléments peut lever si l'entité a été détruite
                f.write(f'Tree,{t.position.x},{t.position.y},{t.position.z},'
                        f'{t.trunk.scale.y},{t.trunk.scale.x},{t.leaves.scale.x},{t.nombre_fruits}\n')
            except Exception:
                continue

        # Houses
        for h in list(house):
            try:
                f.write(f'House,{h.base.position.x},{h.base.position.y},{h.base.position.z}\n')
            except Exception:
                continue

        # Enemies
        for en in list(list_enemy):
            try:
                f.write(f'Enemy,{en.enemy_position.x},{en.enemy_position.y},{en.enemy_position.z},'
                        f'{en.enemy_speed},{en.enemy_damage},{en.enemy_pv}\n')
            except Exception:
                continue



# --- Entrées ---
def input(key):
    global current_spell, door_open, now_spell, inventory, tree, rock, hotbar, house
    if key == 'escape':
        app.close_window(win=False)

    if key == 'left mouse down':
        # show_dialogue(hotbar.items)
        hit_info = raycast(camera.world_position, camera.forward, distance=5, ignore=[player,])
        if hit_info.hit:
            target = hit_info.entity
            if target == npc:
                show_dialogue("Salut voyageur ! Bonne chance dans ta quête.")
            elif target in house:
                for ho in house:
                    if target == ho:
                        pass
                    elif target == ho.door:    
                        ho.toggle_door()
            elif target in rock:
                for r in rock:
                    if 'Pioche' in hotbar.get_selected_item():
                        # si on frappe une Rock (ou un objet ayant l'attribut nombre_de_pierres)
                        if hasattr(target, 'nombre_de_pierres'):
                            r.nombre_de_pierres -= 1
                            inventory.add_item('Roche')
                            show_dialogue(f"Tu frappes la roche. Pierres restantes: {target.nombre_de_pierres}")
                            if r.nombre_de_pierres <= 0:
                                destroy(target)
                        else:
                            show_dialogue("Rien à miner ici.")
            elif target in tree:
                for te in tree:
                    show_dialogue("Tu frappes un arbre.")
                    if target == te.trunk:
                        show_dialogue("Tu frappes le tronc de l'arbre.")
                        if 'Hache' in hotbar.get_selected_item():
                            if hasattr(target, 'nombre_wood'):
                                inventory.add_item('Bois')
                                te.nombre_wood -= 1
                                show_dialogue(f"Tu coupes du bois de l'arbre. Pommes restantes: {te.nombre_bois}")
                                if te.nommbre_wood <= 0 :
                                    destroy(target)
                            else:
                                show_dialogue("Il n'y a plus de pommes sur cet arbre.")
            else:
                pass  # Ajout d'un bloc vide pour éviter l'erreur d'indentation
            for ho in house:
                if target == ho:
                    pass
                elif target == ho.door:    
                    ho.toggle_door()

    if key in AZERTY_HOTBAR_KEYS:
        hotbar.select_slot(AZERTY_HOTBAR_KEYS[key])
        show_dialogue(f'Slot {hotbar.index+1} sélectionné avec {hotbar.get_selected_item()}')

    
    # Ramasser un objet avec la touche 'f' (utile sur AZERTY)
    if key == 'f':
        hit_info = raycast(camera.world_position, camera.forward, distance=5, ignore=[player,])
        if hit_info.hit:
            target = hit_info.entity
            # objets ramassables définis dans pickup_names
            if target in pickup_names:
                inventory.add_item(pickup_names[target])
                show_dialogue(f"Tu as ramassé {pickup_names[target]}")
                destroy(target)
                if target == pickaxe_world:
                    hotbar.add_item('Pioche')
                if target == haxe:
                    hotbar.add_item('Hache')
            # interaction avec les feuilles d'arbres -> pomme
            for t in tree:
                if target == t.leaves:
                    if t.nombre_fruits > 0:
                        inventory.add_item('Pomme')
                        t.nombre_fruits -= 1
                        break
            
            for t in tree:
                if target == t.trunk:
                    if 'Hache' == hotbar.get_selected_item():
                        if t.nombre_wood > 0 :
                            inventory.add_item("Bois")
                            t.nombre_wood -= 1
                            break
                        else:
                            
                            destroy(t)
            else:
                pass
            

    if key == 'tab':
        mouse.visible = not mouse.visible
        mouse.locked = not mouse.locked

        # Active ou désactive le FirstPersonController
        player.enabled = mouse.locked
        inventory.invent_parent.enabled = not mouse.locked




    if key == 'z':
        cast_spell()
    if key == 'e':
        current_spell = (current_spell + 1) % len(spells)
        now_spell.text = f'Sort sélectionné : {spells[current_spell]}'
    if key == 'q':
        current_spell = (current_spell - 1) % len(spells)
        now_spell.text = f'Sort sélectionné : {spells[current_spell]}'
        
other_players = {}  # pseudo -> Entity
    
    
# --- Update ---
def update():
    global pv, mana, endu, list_enemy
    attack_range = 20
    # --- Barres de stats ---
    pv_bar.scale_x = 0.5 * (pv/pv_max)
    endu_bar.scale_x = 0.5 * (endu/endu_max)
    mana_bar.scale_x = 0.5 * (mana/mana_max)
    pv_bar.position = ((-0.82 + (pv_bar.scale_x/2)), 0.45)
    endu_bar.position = ((-0.82 + (endu_bar.scale_x/2)), 0.4)
    mana_bar.position = ((-0.82 + (mana_bar.scale_x/2)), 0.35)
    pv_text_affichage.text = f'{int(pv)}/{pv_max}'
    endu_text_affichage.text = f'{int(endu)}/{endu_max}'
    mana_text_affichage.text = f'{int(mana)}/{mana_max}'
    save_world()
    # --- Régénération / dépense ---
    if held_keys['shift']:
        endu -= 20 * time.dt
    else:
        endu += 10 * time.dt

    mana += 2 * time.dt
    pv += 1 * time.dt

    pv = clamp(pv, 0, pv_max)
    endu = clamp(endu, 0, endu_max)
    mana = clamp(mana, 0, mana_max)

    # --- Vitesse selon endurance ---
    if held_keys['shift']:
        player.speed = 10 if endu > 0 else 2
    else:
        player.speed = 5
    # Envoi de la position
    client.send_player_state(player.position.x, player.position.y, player.position.z)
    # Lecture des positions des autres joueurs
    with client.lock:
        players = client.server_data.get("players", {})


    for pseudo, data in players.items():
        if pseudo == client.my_pseudo:
            continue

        if pseudo not in other_players:
            other_players[pseudo] = Entity(
                model='cube',
                color=color.blue,
                scale=(1,2,1),
                position=(data["x"], data["y"], data["z"])
            )
        else:
            other_players[pseudo].position = (data["x"], data["y"], data["z"])

    for en in list_enemy:
        if en.enemy_pv > 0:
            # --- IA ennemie ---
            dist = distance_xz(player.position, en.enemy_model.position)
            if dist < attack_range:
                # regarder vers le joueur
                en.enemy_parent.look_at(player.position)
                # se déplacer vers le joueur (déplacement horizontal / plan XZ)
                direction = (player.position - en.enemy_parent.position)
                direction.y = 0
                if direction.length() != 0:
                    direction = direction.normalized()
                    en.enemy_parent.position += direction * en.enemy_speed * time.dt
                    en.enemy_model.position = en.enemy_parent.position + Vec3(0,1,0)
                if dist < 2:
                    pv -= en.enemy_damage * time.dt

    # Update projectiles et collisions avec tous les ennemis
    for bullet in projectiles[:]:  # itérer sur une copie car on peut supprimer
        bullet.position += bullet.forward * bullet.speed * time.dt
        # vérifier collision contre chaque ennemi
        for en in list_enemy[:]:
            if bullet.intersects(en.enemy_model).hit:
                show_dialogue("Tu as touché l'ennemi !")
                en.enemy_pv -= bullet.damage
                try:
                    destroy(bullet)
                except Exception:
                    pass
                if bullet in projectiles:
                    projectiles.remove(bullet)
                # si l'ennemi meurt, détruire ses entités et le retirer de la liste
                if en.enemy_pv <= 0:
                    destroy(en.enemy_model)
                    destroy(en.enemy_parent)
                    if en in list_enemy:
                        list_enemy.remove(en)
                break  # arrête    
        for bullet in projectiles[:]:
            if distance_xz(player, bullet)>= 80:
                try:
                    destroy(bullet)
                except Exception:
                    pass
                if bullet in projectiles:
                    projectiles.remove(bullet)
    


#fetch_users_online_with_progress()



app.run()
