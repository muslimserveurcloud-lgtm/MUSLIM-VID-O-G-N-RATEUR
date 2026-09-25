# Bot Telegram – générateur de vidéos (gratuit, max 30s)

Envoie un texte au bot → il renvoie une courte vidéo (fond en dégradé + texte
centré, effet de zoom léger). Envoie une image avec une légende → l'image
sert de fond et la légende devient le texte affiché.

Aucune API payante : tout est généré localement avec `ffmpeg` / `moviepy` /
`Pillow`. Le seul coût est celui de l'endroit où tu fais tourner le bot
(rien si tu le laisses tourner sur ton téléphone via Termux).

## 1. Créer le bot sur Telegram
1. Parle à [@BotFather](https://t.me/BotFather) sur Telegram.
2. `/newbot`, choisis un nom et un identifiant (doit finir par `bot`).
3. Copie le token qu'il te donne.

## 2. Installer le projet

### Sur Termux (Android)
```bash
pkg update && pkg install python ffmpeg -y
pip install -r requirements.txt
```
Sur Termux, `ffmpeg` du dépôt (`pkg install ffmpeg`) est plus fiable que le
binaire embarqué par `imageio-ffmpeg` (compilé pour PC, pas pour Android).

### Sur un serveur Linux classique / Render
```bash
pip install -r requirements.txt
```
`imageio-ffmpeg` fournit un binaire ffmpeg tout seul, aucune installation
système n'est nécessaire.

## 3. Configurer le token
```bash
cp .env.example .env
# puis édite .env et colle ton token TELEGRAM_BOT_TOKEN
```

## 4. Lancer le bot
```bash
python bot.py
```
Le bot tourne en *polling* : il doit rester actif en permanence pour
répondre (garde Termux ouvert avec `termux-wake-lock`, ou déploie-le comme
Background Worker sur Render).

## Déployer sur Render
- Type de service : **Background Worker** (un Web Service gratuit s'endort
  et coupe le polling).
- Build command : `pip install -r requirements.txt`
- Start command : `python bot.py`
- Ajoute `TELEGRAM_BOT_TOKEN` dans les variables d'environnement du service.

## Limites connues (MVP)
- Pas de police "jolie" garantie si aucune police `.ttf` n'est trouvée sur
  la machine (liste dans `FONT_CANDIDATES` de `video_generator.py`) — ajoute
  ton propre fichier dans `assets/font.ttf` pour un rendu soigné.
- Pas encore de musique de fond.
- Durée calculée automatiquement selon la longueur du texte (entre 4 et 30s).

## Fichiers
- `bot.py` — logique du bot Telegram (commandes, réception texte/image, envoi de la vidéo)
- `video_generator.py` — génération de la vidéo (fond + texte + export MP4)
- `requirements.txt` — dépendances Python
- `.env.example` — modèle de configuration
