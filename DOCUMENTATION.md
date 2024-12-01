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

### Paramètres principaux
Les paramètres sont maintenant automatiquement sauvegardés et validés. Le système inclut :

- Validation des paramètres avant le démarrage :
  - `threshold` : Seuil de détection (entre 0 et 1)
  - `delay` : Délai minimum positif entre deux détections (en secondes)
  - `webhook_url` : URL valide commençant par http:// ou https://
  - `enabled` : État d'activation pour chaque source

- Gestion robuste des erreurs :
  - Vérification des permissions d'écriture
  - Sauvegarde sécurisée avec fichier temporaire
  - Restauration automatique en cas d'erreur
  - Messages d'erreur explicites
  - Gestion des timeouts pour les webhooks

### Mode Développement
En mode développement :
- Lien "Exécuter les tests" dans le footer
- Tests automatisés couvrant :
  - Validation des paramètres
  - Opérations sur les fichiers
  - Préservation des paramètres lors de l'arrêt
  - Test des webhooks

### Sources audio
1. **Microphone local**
   - Sélection du périphérique dans l'interface
   - Configuration du webhook dédié
   - Activation/désactivation indépendante

2. **Flux RTSP**
   - Configuration dans l'interface
   - Support de plusieurs flux
   - Webhooks configurables par flux
   - Activation/désactivation individuelle

3. **Sources VBAN**
   - Support du protocole audio VBAN (Virtual Audio Network)
   - Configuration dynamique des sources VBAN
   - Gestion des flux audio en temps réel
   - Webhooks dédiés par source VBAN
   - Activation/désactivation individuelle des sources
   - Support de plusieurs sources simultanées

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
- `app.py` : Application Flask principale avec gestion des WebSockets
- `audio_detector.py` : Module de détection audio avec MediaPipe
- `templates/index.html` : Interface utilisateur responsive
- `static/css/style.css` : Styles de l'interface
- `static/js/modules/` : Modules JavaScript pour la gestion des détections et configurations
- `static/js/modules/detection.js` : Gestion des détections audio
- `vban_manager.py` : Gestion des sources audio VBAN

### Composants clés
1. **Backend Flask**
   - Gestion des WebSockets avec Socket.IO
   - API REST pour la configuration
   - Gestion des sources audio multiples
   - Système de notifications en temps réel

2. **Détection audio**
   - Modèle MediaPipe pour la classification audio
   - Support multi-sources (microphone/RTSP/VBAN)
   - Système de scoring personnalisé
   - Gestion des délais entre détections

3. **Interface utilisateur**
   - Design moderne avec thème sombre
   - Configuration par cartes
   - Visualisation en temps réel des détections
   - Test des webhooks intégré
   - Indicateurs d'état pour chaque source

## Intégration webhook

Le système envoie une requête POST à l'URL configurée avec gestion des erreurs :
- Retry automatique en cas d'échec
- Timeout configurable
- Test de connexion intégré
- Support SSL/TLS

Format de payload :
```json
{
  "source": "microphone",
  "timestamp": 1234567890,
  "score": 0.95
}
```

## Intégration VBAN

Le système supporte le protocole VBAN (Virtual Audio Network) pour la réception de flux audio en réseau :

### Configuration VBAN
- Ajout dynamique de sources VBAN
- Configuration par source :
  - Nom de la source
  - Adresse IP
  - Port d'écoute
  - Nom du flux
  - URL du webhook
- État d'activation individuel

### Fonctionnalités VBAN
- Détection automatique des flux
- Gestion de la mémoire optimisée
- Support multi-sources
- Nettoyage automatique des ressources
- Gestion des erreurs réseau
- Reconnexion automatique

### Sécurité VBAN
- Validation des paramètres réseau
- Vérification des ports
- Gestion des timeouts
- Protection contre les surcharges

## Serveur RTSP (MediaMTX)

Le serveur MediaMTX intégré permet de :
- Capturer l'audio du microphone en flux RTSP
- Gérer plusieurs sources audio simultanément
- Configurer des webhooks par flux

Configuration dans `mediamtx/mediamtx.yml`

## Fonctionnalités de sécurité

### Validation des paramètres
- Vérification automatique avant le démarrage
- Contrôle des valeurs hors limites
- Validation des URLs de webhook
- Test d'accessibilité des webhooks
- Vérification des permissions d'accès audio

### Gestion des fichiers
- Sauvegarde atomique avec fichiers temporaires
- Gestion des permissions
- Backup automatique des paramètres
- Restauration en cas d'erreur
- Verrouillage des fichiers pendant l'écriture

### Gestion des ressources
- Nettoyage automatique des détecteurs
- Libération des ressources audio
- Gestion des timeouts
- Surveillance des performances

## Tests intégrés
Les tests automatisés vérifient :
1. La validation des paramètres
   - Paramètres requis
   - Valeurs limites
   - Format des URLs
2. Les opérations sur les fichiers
   - Permissions
   - Corruption de fichiers
   - Verrouillage de fichiers
3. La préservation des paramètres
   - Sauvegarde correcte
   - Non-modification lors de l'arrêt
