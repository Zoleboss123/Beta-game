# 🚀 Déploiement sur Render

## Prérequis
- Compte Render (https://render.com)
- Repository GitHub avec le code
- `requirements.txt` à la racine du serveur

## Étapes de déploiement

### 1. Préparer le repository
```bash
cd "c:\Users\vincentbignon\Desktop\Beta jeu\server"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YourUsername/Beta-game.git
git push -u origin main
```

### 2. Créer un service sur Render
1. Aller sur https://dashboard.render.com
2. Cliquer "New +" → "Web Service"
3. Connecter votre repository GitHub
4. Remplir les champs :
   - **Name** : `mmo-server`
   - **Root Directory** : `server`
   - **Runtime** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python server.py`
5. Cliquer "Create Web Service"

### 3. Configurer les variables d'environnement
Dans les paramètres du service (Settings) :
- **PORT** : `10000` (défaut Render)
- **PYTHONUNBUFFERED** : `1`

### 4. Accéder au serveur
Une fois déployé :
- 🌐 Dashboard : `https://mmo-server.onrender.com/`
- 🔌 WebSocket : `wss://mmo-server.onrender.com/ws`
- ❤️ Health : `https://mmo-server.onrender.com/health`

### 5. Mettre à jour la page client
Modifier `game.py` et `site_web_realtime.html` pour utiliser la nouvelle URL Render :
```python
client.SERVER_IP = "mmo-server.onrender.com"
```

## Fichiers importants

- `server.py` : Serveur FastAPI principal
- `requirements.txt` : Dépendances Python
- `render.yaml` : Configuration Render (optionnel)
- `site_web_realtime.html` : Dashboard web (servi à `/`)

## Logs en direct
```bash
render logs mmo-server
```

## Redéployer
Après chaque push sur GitHub, Render redéploie automatiquement.

Pour forcer un redéploiement :
```bash
git commit --allow-empty -m "Force redeploy"
git push
```

---

**Note** : Le plan free de Render redémarre automatiquement après 15 min d'inactivité.
