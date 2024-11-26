from flask import Flask, jsonify, request, render_template
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

app = Flask(__name__)
socketio.init_app(app)  # Initialisation de Socket.IO avec l'app Flask

# Définir le chemin absolu du dossier de l'application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
SETTINGS_BACKUP = os.path.join(BASE_DIR, 'settings.json.backup')
SETTINGS_TEMP = os.path.join(BASE_DIR, 'settings.json.tmp')

# Supposons que tu aies ajouté une fonction is_running() dans live.py pour vérifier si la détection est active

# Variable globale pour le détecteur
detector = None

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
        if 'global' in new_settings:
            current_settings['global'].update(new_settings['global'])
        if 'microphone' in new_settings:
            # S'assurer que device_index est un entier
            if 'device_index' in new_settings['microphone']:
                try:
                    # Convertir en entier si c'est une chaîne
                    device_index = int(new_settings['microphone']['device_index'])
                    new_settings['microphone']['device_index'] = device_index
                except (ValueError, TypeError):
                    print(f"Erreur de conversion de device_index: {new_settings['microphone']['device_index']}")
            current_settings['microphone'].update(new_settings['microphone'])
        if 'rtsp_sources' in new_settings:
            current_settings['rtsp_sources'] = new_settings['rtsp_sources']
        if 'vban' in new_settings:
            current_settings['vban'].update(new_settings['vban'])

        # Sauvegarder dans un fichier temporaire d'abord
        with open(SETTINGS_TEMP, 'w') as f:
            json.dump(current_settings, f, indent=4)
        
        # Si l'écriture a réussi, remplacer le fichier original
        os.replace(SETTINGS_TEMP, SETTINGS_FILE)
        
        return True, "Paramètres sauvegardés avec succès"
            
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde des paramètres: {str(e)}"
        print(error_msg)
        return False, error_msg

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
    
    return render_template('index.html', 
                         settings=settings, 
                         devices=input_devices, 
                         flux=flux['audio_streams'],
                         debug=app.debug)

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

@app.route('/start_detection', methods=['POST'])
def start_detection_route():
    try:
        settings = request.json
        # Sauvegarder les paramètres
        success, message = save_settings(settings)
        if not success:
            return jsonify({'error': message}), 400
            
        # Préparer les paramètres pour start_detection
        detection_params = {
            'model': "yamnet.tflite",
            'max_results': 5,
            'score_threshold': float(settings['global']['threshold']),
            'overlapping_factor': 0.8,
            'socketio': socketio,
            'webhook_url': settings['microphone'].get('webhook_url') if settings['microphone'].get('enabled') else None,
            'delay': float(settings['global']['delay']),
            'audio_source': settings['microphone']['audio_source'],  # Utiliser l'audio_source depuis la section microphone
            'rtsp_url': None
        }
        
        # Si la source est RTSP, ajouter l'URL RTSP
        if detection_params['audio_source'].startswith('rtsp://'):
            detection_params['rtsp_url'] = detection_params['audio_source']
            
        # Démarrer la détection
        if start_detection(**detection_params):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Impossible de démarrer la détection'}), 400
            
    except Exception as e:
        print(f"Erreur lors du démarrage de la détection: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/stop_detection', methods=['POST'])
def stop_detection_route():
    try:
        # Arrêter la détection
        if stop_detection():
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
        # Votre logique de rafraîchissement VBAN ici
        # Retourner la nouvelle liste des sources
        sources = get_vban_sources()  # Fonction à implémenter
        return jsonify({'sources': sources})
    except Exception as e:
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

if __name__ == '__main__':
    socketio.run(app, debug=True, port=16045)  # Modified to use socketio.run instead of app.run
