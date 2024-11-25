from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO  # Modified import to include flask_socketio
from classify import start_detection, stop_detection, is_running
import sounddevice as sd
import json
import requests  # Added import for making HTTP requests
from vban_detector import VBANDetector
import threading
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)  # Added line to initialize SocketIO with the Flask app

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
    print("Tentative de mise à jour des paramètres:", new_settings)
    
    try:
        # Vérifier si le fichier existe déjà
        if os.path.exists(SETTINGS_FILE):
            # Vérifier les permissions du fichier existant
            if not os.access(SETTINGS_FILE, os.W_OK):
                try:
                    # Tenter de modifier les permissions
                    os.chmod(SETTINGS_FILE, 0o666)
                except Exception as e:
                    print(f"Impossible de modifier les permissions: {str(e)}")
                    # Continuer quand même, on essaiera d'écrire

        # Charger les paramètres existants
        settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # Si le fichier est corrompu ou n'existe pas, on repart de zéro
                settings = {}

        # Mise à jour des paramètres
        settings['audio_source'] = new_settings.get('audio_source', 'microphone')
        settings['threshold'] = new_settings.get('threshold', settings.get('threshold', '0.5'))
        settings['delay'] = new_settings.get('delay', settings.get('delay', '2'))
        settings['webhook_url'] = new_settings.get('webhook_url', settings.get('webhook_url', ''))

        # Sauvegarder directement dans le fichier
        try:
            # Écrire d'abord dans un fichier temporaire
            with open(SETTINGS_TEMP, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Si l'écriture a réussi, remplacer le fichier original
            os.replace(SETTINGS_TEMP, SETTINGS_FILE)
            
            print("Paramètres sauvegardés avec succès:", settings)
            return True, "Paramètres sauvegardés avec succès"
            
        except Exception as e:
            error_msg = f"Erreur lors de l'écriture du fichier: {str(e)}"
            print(error_msg)
            return False, error_msg

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
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                print("Paramètres chargés :", settings)
                return settings
    except Exception as e:
        print(f"Erreur lors du chargement des paramètres: {str(e)}")
    return {}

@app.route('/')
def index():
    settings = load_settings()  # Charge les paramètres depuis le fichier JSON
    all_devices = sd.query_devices()  # Obtient la liste de tous les périphériques audio
    flux = load_flux()
    print(flux['audio_streams'])
    input_devices = [device for device in all_devices if device['max_input_channels'] > 0]  # Filtrer pour garder seulement les périphériques d'entrée
    return render_template('index.html', 
                         settings=settings, 
                         devices=input_devices, 
                         flux=flux['audio_streams'],
                         debug=app.debug)  # Ajout de la variable debug

def verify_settings_saved(new_settings, saved_settings):
    """Vérifie que les paramètres ont été correctement sauvegardés"""
    try:
        # Liste des champs à vérifier
        fields_to_check = ['audio_source', 'threshold', 'delay', 'webhook_url']
        
        # Vérifier chaque champ
        for field in fields_to_check:
            if new_settings.get(field) != saved_settings.get(field):
                print(f"Différence détectée pour {field}:")
                print(f"  Attendu: {new_settings.get(field)}")
                print(f"  Sauvegardé: {saved_settings.get(field)}")
                return False
        
        print("Tous les paramètres ont été correctement sauvegardés")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la vérification des paramètres: {str(e)}")
        return False

@app.route('/start_detection', methods=['POST'])
def start_detection_route():
    try:
        data = request.get_json()
        print("\n=== Démarrage de la détection ===")
        print("Paramètres reçus:", json.dumps(data, indent=2))
        
        # Valider les paramètres
        validation_result = validate_settings(data)
        if validation_result is not True:
            print("Échec de la validation:", validation_result)
            return jsonify({'success': False, 'message': validation_result}), 400
        
        # Sauvegarder les paramètres
        success, message = save_settings(data)
        if not success:
            print("Échec de la sauvegarde:", message)
            return jsonify({'success': False, 'message': message}), 500

        # Vérifier que les paramètres ont été correctement sauvegardés
        saved_settings = load_settings()
        if not verify_settings_saved(data, saved_settings):
            error_msg = "Les paramètres n'ont pas été correctement sauvegardés"
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500

        print("Paramètres sauvegardés avec succès")

        # Démarrer la détection
        try:
            settings = {
                'model': 'yamnet.tflite',
                'max_results': 5,
                'score_threshold': float(data.get('threshold', 0.5)),
                'delay': float(data.get('delay', 1.0)),
                'overlapping_factor': 0.5,
                'webhook_url': data.get('webhook_url', ''),
                'audio_source': data.get('audio_source', 'microphone'),
                'rtsp_url': data.get('audio_source') if data.get('audio_source', '').startswith('rtsp://') else None,
            }
            
            if is_running():
                stop_detection()
            
            start_detection(**settings, socketio=socketio)
            print("Détection démarrée avec succès")
            return jsonify({'success': True, 'message': 'Détection démarrée avec succès'})
            
        except Exception as e:
            error_msg = f'Erreur lors du démarrage de la détection: {str(e)}'
            print(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 500

    except Exception as e:
        error_msg = f'Erreur: {str(e)}'
        print(error_msg)
        return jsonify({'success': False, 'message': error_msg}), 500

def validate_settings(settings):
    """Valide les paramètres reçus"""
    try:
        # Vérifier que les champs requis sont présents
        required_fields = ['audio_source', 'threshold', 'delay']
        if not all(field in settings for field in required_fields):
            raise ValueError('Tous les champs requis doivent être renseignés')
        
        # Valider le threshold (entre 0 et 1)
        threshold = float(settings['threshold'])
        if not 0 <= threshold <= 1:
            raise ValueError('La précision doit être comprise entre 0 et 1')
        
        # Valider le delay (positif)
        delay = float(settings['delay'])
        if delay < 0:
            raise ValueError('Le délai doit être positif')
        
        # Valider l'URL du webhook si présente
        webhook_url = settings.get('webhook_url', '')
        if webhook_url:
            if not webhook_url.startswith(('http://', 'https://')):
                raise ValueError('L\'URL du webhook doit commencer par http:// ou https://')
            try:
                requests.get(webhook_url, timeout=2)
            except requests.exceptions.RequestException:
                raise ValueError('L\'URL du webhook n\'est pas accessible')
        
        return True
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Erreur de validation: {str(e)}"

def save_settings_to_file(settings):
    """Sauvegarde les paramètres dans le fichier settings.json"""
    try:
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        raise Exception(f"Erreur lors de la sauvegarde des paramètres: {str(e)}")

@app.route('/clap_detected')  # Added route for clap detection
def clap_detected():
    socketio.emit('clap', {'message': 'Applaudissement détecté!'})
    return "Notification envoyée"

@app.route('/test_webhook', methods=['POST'])
def test_webhook():
    data = request.get_json()
    webhook_url = data['webhook_url']
    try:
        response = requests.post(webhook_url, json={"message": "Test du webhook réussi"})
        return jsonify(success=True, message="Webhook testé avec succès: " + str(response.status_code))
    except requests.exceptions.RequestException as e:
        return jsonify(success=False, message="Échec du test du webhook: " + str(e))

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

@app.route('/stop_detection', methods=['POST'])
def stop_detection_route():
    try:
        stop_detection()
        return jsonify({'success': True, 'message': 'Détection arrêtée avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de l\'arrêt de la détection: {str(e)}'}), 500

# Ajouter ces fonctions de test

def test_settings_validation():
    """Fonction pour tester la validation des paramètres"""
    test_cases = [
        {
            'case': "Paramètres valides",
            'settings': {
                'audio_source': 'microphone',
                'threshold': '0.5',
                'delay': '2',
                'webhook_url': 'http://example.com'
            },
            'expected': True
        },
        {
            'case': "Source audio manquante",
            'settings': {
                'threshold': '0.5',
                'delay': '2'
            },
            'expected': "Tous les champs requis doivent être renseignés"
        },
        {
            'case': "Threshold invalide (hors limites)",
            'settings': {
                'audio_source': 'microphone',
                'threshold': '1.5',
                'delay': '2'
            },
            'expected': "La précision doit être comprise entre 0 et 1"
        },
        {
            'case': "Delay négatif",
            'settings': {
                'audio_source': 'microphone',
                'threshold': '0.5',
                'delay': '-1'
            },
            'expected': "Le délai doit être positif"
        },
        {
            'case': "URL webhook invalide",
            'settings': {
                'audio_source': 'microphone',
                'threshold': '0.5',
                'delay': '2',
                'webhook_url': 'invalid-url'
            },
            'expected': "L'URL du webhook doit commencer par http:// ou https://"
        }
    ]

    for test in test_cases:
        print(f"\nTest: {test['case']}")
        result = validate_settings(test['settings'])
        if result == test['expected']:
            print("✅ Test réussi")
        else:
            print("❌ Test échoué")
            print(f"Attendu: {test['expected']}")
            print(f"Obtenu: {result}")

def test_file_operations():
    """Fonction pour tester les opérations sur les fichiers"""
    test_cases = [
        {
            'case': "Écriture dans un fichier en lecture seule",
            'settings': {'test': 'data'},
            'setup': lambda: create_readonly_file('readonly_settings.json'),
            'cleanup': lambda: cleanup_test_file('readonly_settings.json'),
            'file_path': 'readonly_settings.json',
            'expected_error': "Permission denied"
        },
        {
            'case': "Fichier corrompu",
            'settings': {'test': 'data'},
            'setup': lambda: create_corrupted_file('corrupted_settings.json'),
            'cleanup': lambda: cleanup_test_file('corrupted_settings.json'),
            'file_path': 'corrupted_settings.json',
            'test_type': 'json_read'
        },
        {
            'case': "Fichier temporairement verrouillé",
            'settings': {'test': 'data'},
            'setup': lambda: create_locked_file('locked_settings.json'),
            'cleanup': lambda: cleanup_test_file('locked_settings.json'),
            'file_path': 'locked_settings.json',
            'expected_error': "Permission denied"
        }
    ]

    def create_readonly_file(filename):
        """Crée un fichier en lecture seule"""
        with open(filename, 'w') as f:
            f.write('{}')
        os.chmod(filename, 0o444)  # Lecture seule
        return filename

    def create_corrupted_file(filename):
        """Crée un fichier JSON corrompu"""
        with open(filename, 'w') as f:
            f.write('{invalid json')
        return filename

    def create_locked_file(filename):
        """Crée un fichier et le verrouille"""
        with open(filename, 'w') as f:
            f.write('{}')
        
        if os.name == 'posix':  # Unix/Linux/MacOS
            try:
                os.chmod(filename, 0o000)
                return filename
            except:
                pass
        else:  # Windows
            try:
                # Sur Windows, on essaie de créer un fichier en lecture seule
                os.chmod(filename, 0o444)
            except:
                pass
        return filename

    def cleanup_test_file(filename):
        """Nettoie les fichiers de test"""
        try:
            if os.path.exists(filename):
                os.chmod(filename, 0o666)  # Restaure les permissions
                os.remove(filename)
        except:
            pass

    print("\nTests des opérations sur les fichiers:")
    for test in test_cases:
        print(f"\nTest: {test['case']}")
        filename = None
        try:
            # Préparer le test
            filename = test['setup']()
            
            if test.get('test_type') == 'json_read':
                # Test spécial pour le fichier corrompu : tenter de le lire
                try:
                    with open(filename, 'r') as f:
                        json.load(f)
                    print("❌ Test échoué (devrait générer une erreur)")
                except json.JSONDecodeError:
                    print("✅ Test réussi (erreur JSON attendue générée)")
            else:
                # Tests d'écriture normaux
                try:
                    with open(filename, 'w') as f:
                        json.dump(test['settings'], f)
                    print("❌ Test échoué (devrait générer une erreur)")
                except Exception as e:
                    if test['expected_error'] in str(e):
                        print("✅ Test réussi (erreur attendue générée)")
                    else:
                        print("❌ Test échoué")
                        print(f"Erreur attendue: {test['expected_error']}")
                        print(f"Erreur obtenue: {str(e)}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la configuration du test: {str(e)}")
        
        finally:
            # Nettoyer
            if filename:
                test['cleanup']()

def test_stop_detection_params():
    """Teste que l'arrêt de la détection ne modifie pas les paramètres"""
    print("\nTest: Vérification de la préservation des paramètres lors de l'arrêt")
    
    try:
        # 1. Sauvegarder des paramètres initiaux
        initial_settings = {
            'audio_source': 'microphone',
            'threshold': '0.5',
            'delay': '2',
            'webhook_url': 'http://example.com'
        }
        save_settings(initial_settings)
        
        # 2. Démarrer la détection
        settings = {
            'model': 'yamnet.tflite',
            'max_results': 5,
            'score_threshold': float(initial_settings['threshold']),
            'delay': float(initial_settings['delay']),
            'overlapping_factor': 0.5,
            'webhook_url': initial_settings['webhook_url'],
            'audio_source': initial_settings['audio_source'],
        }
        start_detection(**settings, socketio=socketio)
        
        # 3. Arrêter la détection
        stop_detection()
        
        # 4. Charger et vérifier les paramètres
        final_settings = load_settings()
        
        # Vérifier chaque paramètre
        all_match = True
        for key in ['audio_source', 'threshold', 'delay', 'webhook_url']:
            if initial_settings.get(key) != final_settings.get(key):
                print(f"❌ Différence détectée pour {key}:")
                print(f"  Initial: {initial_settings.get(key)}")
                print(f"  Final: {final_settings.get(key)}")
                all_match = False
        
        if all_match:
            print("✅ Test réussi: Les paramètres sont préservés après l'arrêt")
        else:
            print("❌ Test échoué: Certains paramètres ont été modifiés")
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")

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
            'message': 'Tests terminés, vérifiez les logs du serveur pour les résultats'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de l\'exécution des tests: {str(e)}'
        }), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, port=16045)  # Modified to use socketio.run instead of app.run
