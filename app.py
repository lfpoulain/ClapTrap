from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_socketio import SocketIO
from classify import start_detection, stop_detection, is_running
import sounddevice as sd
import json
import requests
from vban_detector import VBANDetector
import threading
import time
import os
from datetime import datetime
from events import socketio  # Importation de l'instance Socket.IO
from vban_discovery import VBANDiscovery
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'
socketio.init_app(app, cors_allowed_origins="*")

# Définir le chemin absolu du dossier de l'application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
SETTINGS_BACKUP = os.path.join(BASE_DIR, 'settings.json.backup')
SETTINGS_TEMP = os.path.join(BASE_DIR, 'settings.json.tmp')

# Supposons que tu aies ajouté une fonction is_running() dans live.py pour vérifier si la détection est active

# Variable globale pour le détecteur
detector = None

# Instance globale de VBANDiscovery
vban_discovery = None
last_vban_init_attempt = 0
VBAN_INIT_RETRY_DELAY = 5  # secondes

def init_vban_discovery():
    """Initialise la découverte VBAN"""
    global vban_discovery
    
    max_retries = 3
    retry_delay = 2.3  # secondes
    
    for attempt in range(max_retries):
        try:
            if vban_discovery is None:
                vban_discovery = VBANDiscovery()
            
            # Créer et configurer le socket
            if vban_discovery._sock is None:
                vban_discovery._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                vban_discovery._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                vban_discovery._sock.settimeout(0.5)
                vban_discovery._sock.bind((vban_discovery.bind_ip, vban_discovery.bind_port))
                print(f"Socket VBAN initialisé sur {vban_discovery.bind_ip}:{vban_discovery.bind_port}")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation VBAN (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Attente avant nouvelle tentative d'initialisation VBAN ({retry_delay}s)")
                time.sleep(retry_delay)
            if vban_discovery and vban_discovery._sock:
                try:
                    vban_discovery._sock.close()
                except:
                    pass
                vban_discovery._sock = None
    
    print("Échec de l'initialisation VBAN après plusieurs tentatives")
    return False

# Initialiser la découverte VBAN
init_vban_discovery()

@app.before_request
def before_request():
    """S'assure que la découverte VBAN est active avant chaque requête"""
    global vban_discovery
    if not vban_discovery or not vban_discovery.running:
        init_vban_discovery()

# Nettoyer lors de l'arrêt
import atexit

@atexit.register
def cleanup():
    """Nettoie les ressources lors de l'arrêt"""
    global vban_discovery
    if vban_discovery:
        vban_discovery.stop()

class VBANSource:
    def __init__(self, name, ip, port, stream_name, webhook_url, enabled=True):
        self.name = name
        self.ip = ip
        self.port = port
        self.stream_name = stream_name
        self.webhook_url = webhook_url
        self.enabled = enabled

    def to_dict(self):
        return {
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "stream_name": self.stream_name,
            "webhook_url": self.webhook_url,
            "enabled": self.enabled
        }

    @staticmethod
    def from_dict(data):
        return VBANSource(
            name=data.get("name", ""),
            ip=data.get("ip", ""),
            port=data.get("port", 6980),
            stream_name=data.get("stream_name", ""),
            webhook_url=data.get("webhook_url", ""),
            enabled=data.get("enabled", True)
        )

class Settings:
    def __init__(self, settings):
        self.settings = settings

    def get_saved_vban_sources(self):
        sources = self.settings.get("saved_vban_sources", [])
        return [VBANSource.from_dict(source) for source in sources]

    def save_vban_source(self, source: VBANSource):
        if "saved_vban_sources" not in self.settings:
            self.settings["saved_vban_sources"] = []
        
        # Vérifier si la source existe déjà (même IP et stream_name)
        existing_sources = self.settings["saved_vban_sources"]
        for i, existing in enumerate(existing_sources):
            if existing["ip"] == source.ip and existing["stream_name"] == source.stream_name:
                # Mettre à jour la source existante
                existing_sources[i] = source.to_dict()
                self.save()
                return
        
        # Ajouter nouvelle source
        self.settings["saved_vban_sources"].append(source.to_dict())
        self.save()

    def remove_vban_source(self, ip: str, stream_name: str):
        if "saved_vban_sources" not in self.settings:
            return
        
        self.settings["saved_vban_sources"] = [
            source for source in self.settings["saved_vban_sources"]
            if not (source["ip"] == ip and source["stream_name"] == stream_name)
        ]
        self.save()

    def update_vban_source(self, ip: str, stream_name: str, updates: dict):
        if "saved_vban_sources" not in self.settings:
            return
        
        for source in self.settings["saved_vban_sources"]:
            if source["ip"] == ip and source["stream_name"] == stream_name:
                source.update(updates)
                self.save()
                break

def save_settings(new_settings):
    """Sauvegarde les paramètres avec une gestion d'erreurs améliorée"""
    try:
        # Charger les paramètres existants ou utiliser la structure par défaut
        default_settings = {
            "global": {
                "threshold": "0.5",
                "delay": "1.0"
            },
            "microphone": {
                "device_index": "0",
                "audio_source": "default",
                "webhook_url": "",
                "enabled": False
            },
            "rtsp_sources": [],
            "saved_vban_sources": [],  # Ajout de la liste des sources VBAN sauvegardées
            "vban": {
                "stream_name": "",
                "ip": "0.0.0.0",
                "port": 6980,
                "webhook_url": "",
                "enabled": False
            }
        }

        # Charger les paramètres existants s'ils existent
        current_settings = default_settings.copy()
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                current_settings.update(json.load(f))

        # Mettre à jour avec les nouveaux paramètres
        current_settings.update(new_settings)

        # Sauvegarder dans un fichier temporaire d'abord
        with open(SETTINGS_TEMP, 'w') as f:
            json.dump(current_settings, f, indent=4)

        # Faire une sauvegarde de l'ancien fichier si nécessaire
        if os.path.exists(SETTINGS_FILE):
            os.replace(SETTINGS_FILE, SETTINGS_BACKUP)

        # Renommer le fichier temporaire
        os.replace(SETTINGS_TEMP, SETTINGS_FILE)

        return True, "Paramètres sauvegardés avec succès"

    except Exception as e:
        return False, f"Erreur lors de la sauvegarde des paramètres: {str(e)}"

def load_flux():
    try:
        with open('flux.json', 'r') as f:
            flux = json.load(f)
            print("Flux chargés :", flux)  # Ajout d'un log pour le débogage
            return flux
    except FileNotFoundError:
        return {"audio_streams": []}


def load_settings():
    """Charge les paramètres avec gestion d'erreurs améliorée"""
    default_settings = {
        "global": {
            "threshold": "0.5",
            "delay": "1.0"
        },
        "microphone": {
            "device_index": "0",
            "audio_source": "default",
            "webhook_url": "",
            "enabled": False
        },
        "rtsp_sources": [],
        "vban": {
            "stream_name": "",
            "ip": "0.0.0.0",
            "port": 6980,
            "webhook_url": "",
            "enabled": False
        }
    }
    
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                
            # Fusionner avec les paramètres par défaut pour s'assurer que toutes les clés existent
            merged_settings = default_settings.copy()
            merged_settings.update(settings)
            
            # S'assurer que la section microphone contient audio_source
            if 'audio_source' not in merged_settings['microphone']:
                merged_settings['microphone']['audio_source'] = default_settings['microphone']['audio_source']
                
            # Sauvegarder les paramètres fusionnés
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(merged_settings, f, indent=4)
                
            return merged_settings
    except Exception as e:
        print(f"Erreur lors du chargement des paramètres: {str(e)}")
        
    # En cas d'erreur ou si le fichier n'existe pas, créer avec les paramètres par défaut
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(default_settings, f, indent=4)
    
    return default_settings

@app.route('/')
def index():
    settings = load_settings()  # Charge les paramètres depuis le fichier JSON
    all_devices = sd.query_devices()  # Obtient la liste de tous les périphériques audio
    flux = load_flux()
    
    # Convertir les périphériques en dictionnaire avec index et nom
    input_devices = []
    for idx, device in enumerate(all_devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'index': idx,
                'name': device['name']
            })
    
    # Échapper correctement le JSON pour JavaScript
    settings_json = json.dumps(settings).replace("'", "\\'").replace('"', '\\"')
    
    return render_template('index.html', 
                         settings=settings, 
                         devices=input_devices, 
                         flux=flux['audio_streams'],
                         debug=app.debug,
                         settings_json=settings_json)

def verify_settings_saved(new_settings, saved_settings):
    """Vérifie que les paramètres ont été correctement sauvegardés"""
    try:
        # Vérifier les paramètres globaux
        if 'global' in new_settings:
            for field in ['threshold', 'delay', 'chunk_duration', 'buffer_duration']:
                if new_settings['global'].get(field) != saved_settings['global'].get(field):
                    print(f"Différence détectée pour global.{field}:")
                    print(f"  Attendu: {new_settings['global'].get(field)}")
                    print(f"  Sauvegardé: {saved_settings['global'].get(field)}")
                    return False

        # Vérifier les paramètres du microphone
        if 'microphone' in new_settings:
            for field in ['device_index', 'audio_source', 'webhook_url']:
                if new_settings['microphone'].get(field) != saved_settings['microphone'].get(field):
                    print(f"Différence détectée pour microphone.{field}:")
                    print(f"  Attendu: {new_settings['microphone'].get(field)}")
                    print(f"  Sauvegardé: {saved_settings['microphone'].get(field)}")
                    return False

        # Vérifier les sources RTSP si présentes
        if 'rtsp_sources' in new_settings:
            if len(new_settings['rtsp_sources']) != len(saved_settings.get('rtsp_sources', [])):
                print("Différence dans le nombre de sources RTSP")
                return False
            for i, (new_source, saved_source) in enumerate(zip(new_settings['rtsp_sources'], saved_settings['rtsp_sources'])):
                for field in ['name', 'url', 'webhook_url']:
                    if new_source.get(field) != saved_source.get(field):
                        print(f"Différence détectée pour rtsp_sources[{i}].{field}:")
                        print(f"  Attendu: {new_source.get(field)}")
                        print(f"  Sauvegardé: {saved_source.get(field)}")
                        return False

        # Ne pas vérifier les champs à la racine car ils sont maintenant dans les sections appropriées
        print("Tous les paramètres ont été correctement sauvegardés")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la vérification des paramètres: {str(e)}")
        return False

@app.route('/api/detection/start', methods=['POST'])
def start_detection_route():
    try:
        settings = request.json
        # Sauvegarder les paramètres
        success, message = save_settings(settings)
        if not success:
            return jsonify({'error': message}), 400
            
        # Vérifier si le microphone est activé
        if not settings.get('microphone', {}).get('enabled', False):
            print("Microphone désactivé - aucune capture audio ne sera effectuée")
            
        # Préparer les paramètres pour start_detection
        detection_params = {
            'model': "yamnet.tflite",
            'max_results': 5,
            'score_threshold': float(settings['global']['threshold']),
            'overlapping_factor': 0.8,
            'socketio': socketio,
            'webhook_url': settings['microphone'].get('webhook_url') if settings['microphone'].get('enabled') else None,
            'delay': float(settings['global']['delay']),
            'audio_source': settings['microphone'].get('audio_source') if settings['microphone'].get('enabled') else None,
            'rtsp_url': None
        }
        
        # Démarrer la détection
        if start_detection(**detection_params):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Impossible de démarrer la détection'}), 400
            
    except Exception as e:
        print(f"Erreur lors du démarrage de la détection: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/detection/stop', methods=['POST'])
def stop_detection_route():
    try:
        # Arrêter la détection
        if stop_detection():
            # Émettre un événement de statut avant d'arrter
            socketio.emit('detection_status', {'status': 'stopped'})
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Impossible d\'arrêter la détection'}), 400
    except Exception as e:
        print(f"Erreur lors de l'arrêt de la détection: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/test_webhook', methods=['POST'])
def test_webhook():
    try:
        data = request.json
        url = data['url']
        source = data['source']
        
        # Envoyer une requête test au webhook
        response = requests.post(url, json={
            'event': 'test',
            'source': source,
            'timestamp': datetime.now().isoformat()
        })
        
        if response.ok:
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Le webhook a répondu avec le code {response.status_code}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/refresh_vban')
def refresh_vban():
    try:
        print("Récupération des sources VBAN...")  # Debug log
        
        # Utiliser l'instance globale
        sources = vban_discovery.get_active_sources()
        print(f"Sources trouvées: {sources}")  # Debug log
        
        # Formater les sources pour l'interface
        formatted_sources = []
        for source in sources:
            formatted_sources.append({
                'name': source.stream_name,
                'ip': source.ip,
                'port': source.port,
                'channels': source.channels,
                'sample_rate': source.sample_rate,
                'id': f"vban_{source.ip}_{source.port}"
            })
        
        print(f"Sources formatées: {formatted_sources}")  # Debug log
        return jsonify({'sources': formatted_sources})
    except Exception as e:
        print(f"Erreur lors de la rcupération des sources VBAN: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 400

@app.route('/clap_detected')  # Added route for clap detection
def clap_detected():
    socketio.emit('clap', {'message': 'Applaudissement détecté!'})
    return "Notification envoyée"

@app.route('/status')
def status():
    try:
        running = is_running()
        return jsonify({'running': running})
    except Exception as e:
        return jsonify({'running': False, 'error': str(e)})

@app.route('/refresh_vban_sources')
def refresh_vban_sources():
    detector = VBANDetector.get_instance()
    
    # Make sure the detector is running
    if not detector.running:
        # Start listening in a separate thread
        thread = threading.Thread(target=detector.start_listening)
        thread.daemon = True
        thread.start()
        
        # Give it a moment to detect sources
        time.sleep(2)
    
    active_sources = detector.get_active_sources()
    
    vban_sources = []
    for ip, info in active_sources.items():
        source_name = info.get('name', '').strip()
        if source_name:  # Only add sources with valid names
            vban_sources.append({
                "name": f"VBAN: {source_name} ({ip})",
                "url": f"vban://{ip}"
            })
    
    # Stop the detector if we started it just for the refresh
    if not detector.running:
        detector.stop_listening()
    
    return jsonify({"sources": vban_sources})

def test_settings_validation():
    """Test de la validation des paramètres"""
    print("\n1. Test de validation des paramètres basiques")
    test_settings = {
        'global': {
            'threshold': '0.5',
            'delay': '1.0',
            'chunk_duration': 0.5,
            'buffer_duration': 1.0
        },
        'microphone': {
            'device_index': '0',
            'audio_source': 'Test Microphone',
            'webhook_url': 'http://test.com/webhook'
        }
    }
    
    success, _ = save_settings(test_settings)
    print(f"Test basique: {'✓' if success else '✗'}")

    print("\n2. Test avec des valeurs invalides")
    invalid_settings = {
        'global': {
            'threshold': 'invalid',
            'delay': -1,
        }
    }
    success, _ = save_settings(invalid_settings)
    print(f"Test valeurs invalides: {'✓' if not success else '✗'}")

def test_file_operations():
    """Test des opérations sur les fichiers"""
    print("\n1. Test de sauvegarde des paramètres")
    test_settings = {
        'global': {
            'threshold': '0.5',
            'delay': '1.0'
        }
    }
    success, _ = save_settings(test_settings)
    print(f"Sauvegarde: {'✓' if success else '✗'}")

    print("\n2. Test de lecture des paramètres")
    settings = load_settings()
    print(f"Lecture: {'✓' if settings else '✗'}")

def test_stop_detection_params():
    """Test de la préservation des paramètres lors de l'arrêt"""
    print("\n1. Test de sauvegarde avant arrêt")
    initial_settings = load_settings()
    print(f"Paramètres initiaux chargés: {'✓' if initial_settings else '✗'}")

    print("\n2. Test après arrêt")
    stop_detection()
    final_settings = load_settings()
    print(f"Paramètres préservés: {'✓' if final_settings == initial_settings else '✗'}")

@app.route('/run_tests', methods=['POST'])
def run_tests():
    """Route pour exécuter les tests"""
    try:
        print("\n=== Démarrage des tests ===")
        
        print("\nTests de validation des paramètres:")
        test_settings_validation()
        
        print("\nTests des opérations sur les fichiers:")
        test_file_operations()
        
        print("\nTest de préservation des paramètres:")
        test_stop_detection_params()
        
        return jsonify({
            'success': True,
            'message': 'Tests terminés avec succès'
        })
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/save_settings', methods=['POST'])
def save_settings_route():
    try:
        settings = request.json
        if not settings:
            return jsonify({'error': 'Aucun paramètre fourni'}), 400
            
        success, message = save_settings(settings)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def validate_settings(settings):
    """Valide les paramètres avant la sauvegarde"""
    required_fields = ['threshold', 'delay', 'audio_source']
    
    # Vérifier les champs requis
    if not all(field in settings for field in required_fields):
        return False
        
    # Valider les valeurs
    try:
        threshold = float(settings['threshold'])
        delay = float(settings['delay'])
        
        if not (0 <= threshold <= 1):
            return False
        if delay < 0:
            return False
            
        # Valider l'URL du webhook si présente
        if settings.get('microphone', {}).get('webhook_url'):
            url = settings['microphone']['webhook_url']
            if not url.startswith(('http://', 'https://')):
                return False
                
    except (ValueError, TypeError):
        return False
        
    return True

@socketio.on('clap_detected')
def handle_clap(source_type, source_id):
    print(f"Clap detected from {source_type} - {source_id}")  # Log pour debug
    socketio.emit('clap_detected', {
        'source_type': source_type,
        'source_id': source_id,
        'timestamp': time.time()
    })

@app.route('/api/vban/save', methods=['POST'])
def save_vban_source():
    try:
        source = request.json
        print(f"Réception demande d'ajout source VBAN: {source}")  # Debug log
        
        # Valider les données requises
        required_fields = ['name', 'ip', 'port']
        if not all(field in source for field in required_fields):
            print(f"Champs manquants. Reçu: {source}")  # Debug log
            return jsonify({
                'success': False,
                'error': 'Données manquantes pour la source VBAN'
            }), 400
        
        # Charger les paramètres actuels
        settings = load_settings()
        
        # Initialiser la liste si elle n'existe pas
        if 'saved_vban_sources' not in settings:
            settings['saved_vban_sources'] = []
            
        # Vérifier si la source existe déjà
        existing_source = next(
            (s for s in settings['saved_vban_sources'] 
             if s['ip'] == source['ip'] and s['name'] == source['name']),
            None
        )
        
        if existing_source:
            print(f"Source déjà existante: {existing_source}")  # Debug log
            return jsonify({
                'success': False,
                'error': 'Cette source VBAN existe déjà'
            }), 400
            
        # Ajouter la nouvelle source
        new_source = {
            'name': source['name'],
            'ip': source['ip'],
            'port': source['port'],
            'stream_name': source['name'],  # Utiliser le nom comme stream_name
            'webhook_url': source.get('webhook_url', ''),
            'enabled': source.get('enabled', True)
        }
        
        settings['saved_vban_sources'].append(new_source)
        
        # Sauvegarder immédiatement les paramètres
        success, message = save_settings(settings)
        
        if success:
            print(f"Source VBAN sauvegardée avec succès: {new_source}")  # Debug log
            return jsonify({
                'success': True,
                'source': new_source
            })
        else:
            print(f"Erreur lors de la sauvegarde des paramètres: {message}")  # Debug log
            return jsonify({
                'success': False,
                'error': f"Erreur lors de la sauvegarde: {message}"
            }), 500
            
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la source VBAN: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vban/remove', methods=['DELETE'])
def remove_vban_source():
    try:
        data = request.json
        if not data or 'ip' not in data or 'stream_name' not in data:
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
            
        settings = load_settings()
        
        if 'saved_vban_sources' not in settings:
            return jsonify({
                'success': False,
                'error': 'Aucune source VBAN configurée'
            }), 404
            
        # Filtrer la source à supprimer
        initial_count = len(settings['saved_vban_sources'])
        settings['saved_vban_sources'] = [
            s for s in settings['saved_vban_sources']
            if not (s['ip'] == data['ip'] and s['stream_name'] == data['stream_name'])
        ]
        
        if len(settings['saved_vban_sources']) == initial_count:
            return jsonify({
                'success': False,
                'error': 'Source non trouvée'
            }), 404
            
        # Sauvegarder les modifications
        success, message = save_settings(settings)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        print(f"Erreur lors de la suppression de la source VBAN: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vban/update', methods=['PUT'])
def update_vban_source():
    try:
        source = request.json
        print(f"Mise à jour source VBAN reçue: {source}")  # Debug log
        
        if not source or 'ip' not in source:
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
            
        settings = load_settings()
        
        if 'saved_vban_sources' not in settings:
            settings['saved_vban_sources'] = []
            
        # Trouver et mettre à jour la source
        source_found = False
        for s in settings['saved_vban_sources']:
            if (s['ip'] == source['ip'] and 
                (s['stream_name'] == source.get('stream_name') or 
                 s['stream_name'] == source.get('name'))):
                # Mettre à jour tous les champs fournis
                for key in ['name', 'port', 'stream_name', 'webhook_url', 'enabled']:
                    if key in source:
                        s[key] = source[key]
                source_found = True
                break
                
        if not source_found:
            print(f"Source non trouvée. Sources existantes: {settings['saved_vban_sources']}")  # Debug log
            return jsonify({
                'success': False,
                'error': 'Source non trouvée'
            }), 404
            
        # Sauvegarder les modifications
        success, message = save_settings(settings)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la source VBAN: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/js/modules/<path:filename>')
def serve_js_module(filename):
    return send_from_directory('static/js/modules', filename, mimetype='application/javascript')

@app.route('/api/audio-sources', methods=['GET'])
def get_audio_sources():
    try:
        devices = sd.query_devices()
        audio_sources = [
            {
                'index': idx,
                'name': device['name'],
                'type': 'microphone'
            }
            for idx, device in enumerate(devices)
            if device['max_input_channels'] > 0
        ]
        return jsonify(audio_sources)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rtsp/streams', methods=['GET'])
def get_rtsp_streams():
    try:
        settings = load_settings()
        return jsonify(settings.get('rtsp_sources', []))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vban/sources', methods=['GET'])
def get_vban_sources():
    try:
        # S'assurer que la découverte VBAN est initialisée
        if not init_vban_discovery():
            return jsonify({'error': 'Impossible d\'initialiser la découverte VBAN'}), 500
            
        # Effectuer un scan rapide
        start_time = time.time()
        active_sources = []
        logged_sources = set()  # Pour suivre les sources déjà loggées
        
        try:
            while time.time() - start_time < 1.0:  # Scan pendant 1 seconde
                try:
                    data, addr = vban_discovery._sock.recvfrom(2048)
                    if len(data) >= 4 and data[:4] == b'VBAN':
                        source = vban_discovery._parse_vban_packet(data, addr, logged_sources)
                        if source:
                            source_key = f"{source.ip}:{source.port}"
                            # Éviter les doublons
                            if not any(s.ip == source.ip and s.port == source.port for s in active_sources):
                                active_sources.append(source)
                                logged_sources.add(source_key)
                except socket.timeout:
                    continue
                    
        except Exception as e:
            print(f"Erreur pendant le scan VBAN: {e}")
            
        print(f"Sources VBAN actives trouvées: {len(active_sources)}")
        formatted_sources = [source.to_dict() for source in active_sources]
        print(f"Sources formatées: {formatted_sources}")
        return jsonify(formatted_sources)
        
    except Exception as e:
        print(f"Erreur lors de la récupération des sources VBAN: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vban/saved-sources', methods=['GET'])
def get_saved_vban_sources():
    try:
        settings = load_settings()
        saved_sources = settings.get('saved_vban_sources', [])
        print(f"Sources VBAN sauvegardées trouvées: {len(saved_sources)}")  # Debug log
        print(f"Sources: {saved_sources}")  # Debug log
        return jsonify(saved_sources)
    except Exception as e:
        print(f"Erreur lors de la récupération des sources VBAN sauvegardées: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/save', methods=['POST'])
def save_settings_api():
    try:
        settings = request.json
        if not settings:
            return jsonify({'error': 'Aucun paramètre fourni'}), 400
            
        success, message = save_settings(settings)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    try:
        # Désactiver le mode debug
        socketio.run(app, host='127.0.0.1', port=16045, debug=False)
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur: {e}")
        cleanup()
