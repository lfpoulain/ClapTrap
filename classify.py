import time
import requests
import ffmpeg
import logging
import numpy as np
import sounddevice as sd
from mediapipe.tasks import python
from mediapipe.tasks.python.components import containers
from mediapipe.tasks.python import audio
from flask_socketio import SocketIO
import json
import warnings
import wave
import os
import pyaudio
import collections
import cv2
import sys
from events import send_clap_event, send_labels
import threading
from vban_manager import get_vban_detector  # Import the get_vban_detector function
import warnings
from audio_detector import AudioDetector

# Configuration du logging en DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")

# Variables globales
detection_running = False
classifier = None
record = None
model = "yamnet.tflite"
output_file = "recorded_audio.wav"
current_audio_source = None
_socketio = None  # Renamed to _socketio to avoid conflict with parameter

def reload_settings():
    """Recharge les paramètres depuis le fichier settings.json"""
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erreur lors du rechargement des paramètres: {e}")
        return None

# Charger les paramètres depuis settings.json
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
        
    # Récupérer la source audio depuis la section microphone
    microphone_settings = settings.get('microphone', {})
    if microphone_settings is None:
        microphone_settings = {}
    AUDIO_SOURCE = microphone_settings.get('audio_source')
    
    # Ne pas lever d'erreur si audio_source n'est pas défini, on le gérera au moment de start_detection
    if not AUDIO_SOURCE:
        logging.warning("Aucune source audio n'est définie dans settings.json")
        
    # Récupérer les paramètres globaux avec des valeurs par défaut
    global_settings = settings.get('global', {})
    if global_settings is None:
        global_settings = {}
        
    THRESHOLD = float(global_settings.get('threshold', 0.5))
    DELAY = float(global_settings.get('delay', 2))
    CHUNK_DURATION = float(global_settings.get('chunk_duration', 0.5))
    BUFFER_DURATION = float(global_settings.get('buffer_duration', 1.0))
    
except FileNotFoundError:
    logging.warning("Le fichier settings.json n'existe pas, utilisation des valeurs par défaut")
    AUDIO_SOURCE = None
    THRESHOLD = 0.5
    DELAY = 2.0
    CHUNK_DURATION = 0.5
    BUFFER_DURATION = 1.0
except json.JSONDecodeError:
    logging.error("Le fichier settings.json est mal formaté")
    raise
except Exception as e:
    logging.error(f"Erreur lors du chargement des paramètres: {str(e)}")
    raise

# Charger les flux RTSP et leurs webhooks associés
try:
    with open("settings.json") as f:
        settings_data = json.load(f)
        fluxes = settings_data.get('rtsp_streams', {})
except FileNotFoundError:
    logging.warning("Le fichier settings.json n'existe pas, aucun flux RTSP ne sera chargé")
    fluxes = {}
except json.JSONDecodeError:
    logging.error("Le fichier settings.json est mal formaté")
    fluxes = {}
except Exception as e:
    logging.error(f"Erreur lors du chargement des flux RTSP: {str(e)}")
    fluxes = {}

def save_audio_to_wav(audio_data, sample_rate, filename):
    if not audio_data.size:
        logging.warning("No audio data to save.")
        return
    try:
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 2 bytes per sample
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        logging.info(f"Audio saved to {filename}")
    except Exception as e:
        logging.error(f"Failed to save audio to {filename}: {e}")

def read_audio_from_rtsp(rtsp_url, buffer_size):
    """Lit un flux RTSP audio en continu sans buffer fichier"""
    try:
        # Configuration du processus ffmpeg pour lire le flux RTSP
        process = (
            ffmpeg
            .input(rtsp_url)
            .output('pipe:', 
                   format='f32le',  # Format PCM 32-bit float
                   acodec='pcm_f32le', 
                   ac=1,  # Mono
                   ar='16000',
                   buffer_size='64k'  # Réduire la taille du buffer
            )
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        while True:
            # Lecture des données audio par blocs
            in_bytes = process.stdout.read(buffer_size * 4)  # 4 bytes par sample float32
            if not in_bytes:
                break
                
            # Conversion en numpy array
            audio_chunk = np.frombuffer(in_bytes, np.float32)
            
            if len(audio_chunk) > 0:
                yield audio_chunk.reshape(-1, 1)
            
    except Exception as e:
        logging.error(f"Erreur lors de la lecture RTSP: {e}")
        yield None
    finally:
        if process:
            process.kill()

def start_detection(
    model,
    max_results,
    score_threshold: float,
    overlapping_factor,
    socketio: SocketIO,
    webhook_url: str,
    delay: float,
    audio_source: str,
    rtsp_url: str = None,
):
    global detection_running, classifier, record, current_audio_source, _socketio
    
    try:
        if detection_running:
            return False

        # Recharger les paramètres pour avoir les dernières modifications
        settings = reload_settings()
        if settings:
            microphone_settings = settings.get('microphone', {})
            if isinstance(microphone_settings, dict) and microphone_settings.get('enabled', False):
                # Utiliser les paramètres du microphone les plus récents
                audio_source = microphone_settings.get('audio_source')
                logging.info(f"Utilisation du microphone: {audio_source}")

        detection_running = True
        current_audio_source = audio_source
        _socketio = socketio  # Store the socketio instance globally

        if (overlapping_factor <= 0) or (overlapping_factor >= 1.0):
            raise ValueError("Overlapping factor must be between 0 and 1.")

        if (score_threshold < 0) or (score_threshold > 1.0):
            raise ValueError("Score threshold must be between (inclusive) 0 et 1.")

        # Démarrer la détection dans un thread séparé
        detection_thread = threading.Thread(target=run_detection, args=(
            model,
            max_results,
            score_threshold,
            overlapping_factor,
            socketio,
            webhook_url,
            delay,
            audio_source,
            rtsp_url
        ))
        detection_thread.daemon = True
        detection_thread.start()
        
        return True
        
    except Exception as e:
        logging.error(f"Erreur pendant le démarrage de la détection: {e}")
        detection_running = False
        return False

def run_detection(model, max_results, score_threshold, overlapping_factor, socketio, webhook_url, delay, audio_source, rtsp_url):
    """Fonction qui exécute la détection dans un thread séparé"""
    try:
        # Initialiser le détecteur audio
        detector = AudioDetector(model, sample_rate=16000, buffer_duration=1.0)
        detector.initialize()
        
        def create_detection_callback(source_name, webhook_url=None):
            def handle_detection(detection_data):
                try:
                    logging.info(f"CLAP détecté sur {source_name} avec score {detection_data['score']}")
                    if socketio:
                        socketio.emit('clap', {
                            'source_id': source_name,
                            'timestamp': detection_data['timestamp'],
                            'score': detection_data['score']
                        })
                    
                    # Utiliser le webhook_url passé au callback
                    if webhook_url:
                        logging.info(f"Envoi webhook pour {source_name} vers {webhook_url}")
                        requests.post(webhook_url)
                except Exception as e:
                    logging.error(f"Erreur lors de l'envoi de l'événement clap pour {source_name}: {str(e)}")
            return handle_detection
        
        def create_labels_callback(source_name):
            def handle_labels(labels):
                logging.debug(f"Labels détectés sur {source_name}: {labels}")
                if socketio:
                    socketio.emit("labels", {"source": source_name, "detected": labels})
            return handle_labels
        
        # Vérifier si une source audio est configurée
        if not audio_source:
            logging.error("Aucune source audio n'est configurée ou active")
            return
            
        # Initialiser la source audio en fonction du paramètre audio_source
        if audio_source.startswith("rtsp"):
            if not rtsp_url:
                raise ValueError("RTSP URL must be provided for RTSP audio source.")
                
            source_id = f"rtsp_{rtsp_url}"
            
            # Récupérer le webhook_url depuis les paramètres RTSP
            settings = reload_settings()
            rtsp_webhook_url = None
            if settings and 'rtsp_sources' in settings:
                for source in settings['rtsp_sources']:
                    if source.get('url') == rtsp_url and source.get('enabled', True):
                        rtsp_webhook_url = source.get('webhook_url')
                        break
            
            # Utiliser le webhook spécifique à la source RTSP s'il existe, sinon utiliser celui par défaut
            webhook_url_to_use = rtsp_webhook_url or webhook_url
            
            detector.add_source(
                source_id=source_id,
                detection_callback=create_detection_callback(source_id, webhook_url_to_use),
                labels_callback=create_labels_callback(source_id)
            )
            
            # Démarrer la détection
            detector.start()
            logging.info(f"Détection démarrée pour la source RTSP {source_id}")
            
            rtsp_reader = read_audio_from_rtsp(rtsp_url, int(16000 * 0.1))  # Buffer de 100ms
            while detection_running:
                audio_data = next(rtsp_reader)
                detector.process_audio(audio_data, source_id)
                
        elif audio_source.startswith("vban://"):
            vban_ip = audio_source.replace("vban://", "")
            source_id = f"vban_{vban_ip}"
            
            # Récupérer le webhook_url depuis les paramètres VBAN
            settings = reload_settings()
            vban_webhook_url = None
            if settings and 'saved_vban_sources' in settings:
                for source in settings['saved_vban_sources']:
                    if source.get('ip') == vban_ip and source.get('enabled', True):
                        vban_webhook_url = source.get('webhook_url')
                        break
            
            # Utiliser le webhook spécifique à la source VBAN s'il existe, sinon utiliser celui par défaut
            webhook_url_to_use = vban_webhook_url or webhook_url
            
            detector.add_source(
                source_id=source_id,
                detection_callback=create_detection_callback(source_id, webhook_url_to_use),
                labels_callback=create_labels_callback(source_id)
            )
            
            # Démarrer la détection
            detector.start()
            logging.info(f"Détection démarrée pour la source VBAN {source_id} avec webhook {webhook_url_to_use}")
            
            vban_detector = get_vban_detector()
            
            def audio_callback(audio_data, timestamp):
                if not detection_running:
                    return
                    
                active_sources = vban_detector.get_active_sources()
                if vban_ip not in active_sources:
                    return
                    
                detector.process_audio(audio_data, source_id)
            
            vban_detector.set_audio_callback(audio_callback)
            
            # Maintenir le thread en vie tant que la détection est active
            while detection_running:
                time.sleep(0.1)  # Éviter de surcharger le CPU
                
                # Vérifier périodiquement si la source est toujours active
                active_sources = vban_detector.get_active_sources()
                if vban_ip not in active_sources:
                    logging.warning(f"Source VBAN {vban_ip} non trouvée")
                    time.sleep(1)  # Attendre un peu plus longtemps avant la prochaine vérification
                    
        else:  # Microphone
            # Récupérer l'index du périphérique depuis les paramètres
            settings = reload_settings()
            device_index = int(settings.get('microphone', {}).get('device_index', 0))
            source_id = f"mic_{device_index}"
            
            # Récupérer le webhook_url depuis les paramètres du microphone
            microphone_webhook_url = settings.get('microphone', {}).get('webhook_url')
            webhook_url_to_use = microphone_webhook_url or webhook_url
            
            detector.add_source(
                source_id=source_id,
                detection_callback=create_detection_callback(source_id, webhook_url_to_use),
                labels_callback=create_labels_callback(source_id)
            )
            
            # Démarrer la détection
            detector.start()
            logging.info(f"Détection démarrée pour la source microphone {source_id}")
            
            with sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=16000,
                blocksize=int(16000 * 0.1),  # Buffer de 100ms
                callback=lambda indata, frames, time, status: detector.process_audio(indata[:, 0], source_id)
            ):
                logging.info("Stream audio démarré pour le microphone")
                while detection_running:
                    time.sleep(0.1)
                    
        detector.stop()
        return True
        
    except Exception as e:
        logging.error(f"Erreur dans run_detection: {str(e)}")
        return False

def stop_detection():
    """Arrête la détection"""
    global detection_running, classifier, record, current_audio_source, _socketio
    
    try:
        detection_running = False
        
        # Notify clients that detection has stopped
        if _socketio:
            _socketio.emit("detection_status", {"status": "stopped"})
        
        if record:
            record.stop()
            record.close()
            record = None
            
        if classifier:
            classifier.close()
            classifier = None

        current_audio_source = None  # Réinitialisation de la source audio
        
        return True  # Retourner True si tout s'est bien passé
        
    except Exception as e:
        logging.error(f"Erreur lors de l'arrêt de la détection: {e}")
        return False  # Retourner False en cas d'erreur

def is_running():
    return detection_running

# Ajout d'une commande simple pour démarrer et arrêter la détection pour les tests
if __name__ == "__main__":
    try:
        socketio = SocketIO()
        start_detection(
            model=model,
            max_results=5,
            score_threshold=0.5,
            overlapping_factor=0.8,
            socketio=socketio,
            webhook_url="http://example.com/webhook",
            delay=2.0,
            audio_source=audio_source,
            rtsp_url=rtsp_url,
        )
    except KeyboardInterrupt:
        logging.info("Detection stopped by user.")
        stop_detection()
