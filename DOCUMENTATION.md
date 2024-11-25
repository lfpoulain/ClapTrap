# ClapTrap - Détection d'applaudissements en temps réel

ClapTrap est une application web qui utilise un modèle de classification audio YAMNet pré-entraîné pour détecter les applaudissements en temps réel à partir de différentes sources audio (microphone local ou flux RTSP). Lorsqu'un applaudissement est détecté, une notification est envoyée via un webhook configurable.

## Prérequis

- Python 3.11
- Dépendances listées dans `requirements.txt` + pytorch Apple Silicon si besoin : pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu
- FFmpeg (pour le support RTSP)
- MediaMTX (pour le serveur RTSP)

## Installation

1. Clonez le dépôt et installez les dépendances :

```bash
git clone https://github.com/yourusername/claptrap.git
cd claptrap
python3.11 -m venv claptrap
source claptrap/bin/activate
pip install -r requirements.txt
```

2. Configurez le serveur RTSP (optionnel) :
```bash
cd mediamtx
./mediamtx
```

3. Lancez l'application Flask :
```bash
python app.py
```

4. Ouvrez votre navigateur à l'adresse `http://localhost:16045`

## Configuration

### Paramètres principaux (settings.json)
- `threshold` : Seuil de détection (entre 0 et 1)
- `delay` : Délai minimum entre deux détections (en secondes)
- `webhook_url` : URL du webhook pour les notifications
- `audio_source` : Source audio (microphone ou URL RTSP)
- `rtsp_url` : URL du flux RTSP (si utilisé)

### Sources audio
1. **Microphone local**
   - Sélection du périphérique dans l'interface
   - Configuration automatique

2. **Flux RTSP**
   - Configuration dans `flux.json`
   - Support de plusieurs flux avec webhooks dédiés

## Utilisation

1. Sélectionnez la source audio dans les paramètres :
   - Microphone local
   - Flux RTSP disponibles

2. Configurez les paramètres de détection :
   - Seuil de détection
   - Délai entre détections
   - URL du webhook

3. Cliquez sur "Démarrer la détection" pour lancer la détection en temps réel.

4. Lorsqu'un applaudissement est détecté :
   - Une notification "👏" s'affiche
   - Un événement est envoyé au webhook configuré
   - Les sons détectés sont listés en temps réel

5. Cliquez sur "Arrêter la détection" pour stopper le processus.

## Architecture technique

### Fichiers principaux
- `app.py` : Application Flask principale gérant l'interface web et les interactions
- `classify.py` : Module de détection d'applaudissements utilisant MediaPipe
- `templates/index.html` : Interface utilisateur responsive
- `static/css/style.css` : Styles de l'interface
- `static/js/script.js` : Interactions côté client
- `mediamtx/` : Serveur RTSP pour la gestion des flux audio

### Composants clés
1. **Backend Flask**
   - Gestion des WebSockets pour les mises à jour en temps réel
   - API REST pour le contrôle de la détection
   - Configuration des paramètres

2. **Détection audio**
   - Modèle YAMNet pré-entraîné
   - Support multi-sources (microphone/RTSP)
   - Filtrage intelligent des faux positifs

3. **Interface utilisateur**
   - Design moderne et responsive
   - Visualisation en temps réel
   - Configuration intuitive

## Intégration webhook

Le système envoie une requête POST à l'URL configurée lors de chaque détection. Compatible avec :
- Home Assistant
- Node-RED
- Services web personnalisés

Exemple d'URL webhook Home Assistant :
```
http://homeassistant.local:8123/api/webhook/claptrap
```

## Serveur RTSP (MediaMTX)

Le serveur MediaMTX intégré permet de :
- Capturer l'audio du microphone en flux RTSP
- Gérer plusieurs sources audio simultanément
- Configurer des webhooks par flux

Configuration dans `mediamtx/mediamtx.yml`