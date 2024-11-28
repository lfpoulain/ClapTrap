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
from events import send_clap_event, send_labels
import threading
from vban_manager import get_vban_detector  # Import the get_vban_detector function
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")
logging.basicConfig(level=logging.INFO)

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
with open("flux.json") as f:
    fluxes = json.load(f)

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
        classification_result_list = []

        def save_result(result: audio.AudioClassifierResult, timestamp_ms: int):
            result.timestamp_ms = timestamp_ms
            classification_result_list.append(result)

        # Initialize the audio classification model.
        base_options = python.BaseOptions(model_asset_path=model)
        options = audio.AudioClassifierOptions(
            base_options=base_options,
            running_mode=audio.RunningMode.AUDIO_STREAM,
            max_results=max_results,
            score_threshold=score_threshold,
            result_callback=save_result,
        )
        classifier = audio.AudioClassifier.create_from_options(options)

        # Initialize the audio recorder and a tensor to store the audio input.
        duration = 0.1  # Réduire de 1.0 à 0.1 seconde
        sample_rate = 16000
        num_channels = 1
        buffer_size = int(duration * sample_rate * num_channels)
        audio_format = containers.AudioDataFormat(num_channels, sample_rate)
        audio_data = containers.AudioData(buffer_size, audio_format)

        input_length_in_second = (
            float(len(audio_data.buffer)) / audio_data.audio_format.sample_rate
        )
        interval_between_inference = input_length_in_second * (1 - overlapping_factor)
        pause_time = interval_between_inference * 0.05
        last_inference_time = time.time()
        last_clap_time = 0  # Initialiser le temps de la dernière détection

        # Initialiser la source audio en fonction du paramètre audio_source
        logging.info("Audio source : %s", audio_source)
        
        if not audio_source:
            logging.error("Aucune source audio spécifiée")
            return False
            
        if audio_source.startswith("rtsp"):
            if not rtsp_url:
                raise ValueError("RTSP URL must be provided for RTSP audio source.")
            logging.info("RTSP")
            # Utiliser PyAudio pour lire le flux RTSP
            rtsp_reader = read_audio_from_rtsp(rtsp_url, buffer_size)
        elif audio_source.startswith("vban://"):
            # Extraire l'IP du format vban://IP
            vban_ip = audio_source.replace("vban://", "")
            logging.info(f"Démarrage de l'écoute VBAN sur l'IP {vban_ip}")
            detector = get_vban_detector()  # Get the global VBAN detector instance
            
            def audio_callback(audio_data, timestamp):
                try:
                    # Vérifier que les données viennent de la bonne source
                    active_sources = detector.get_active_sources()
                    if vban_ip not in active_sources:
                        return  # Ignorer les données si elles ne viennent pas de la source configurée
                        
                    # Convertir en format attendu par le classificateur
                    # Ensure audio_data is the right shape (samples,)
                    if len(audio_data.shape) > 1:
                        audio_data = audio_data.flatten()
                    
                    # Ensure we have the right number of samples
                    target_samples = int(0.975 * 16000)  # ~975ms at 16kHz
                    if len(audio_data) > target_samples:
                        audio_data = audio_data[:target_samples]
                    elif len(audio_data) < target_samples:
                        # Pad with zeros if we have too few samples
                        padding = np.zeros(target_samples - len(audio_data))
                        audio_data = np.concatenate([audio_data, padding])
                    
                    # Reshape for the classifier (samples, 1)
                    audio_data = audio_data.reshape(-1, 1)
                    
                    # Convert to AudioData format
                    audio_data = containers.AudioData.create_from_array(
                        audio_data,
                        containers.AudioDataFormat(1, 16000)
                    )
                    
                    # Process with classifier
                    classifier.classify_async(audio_data, round(timestamp * 1000))
                    
                    # Traiter les résultats de classification
                    if classification_result_list:
                        classification = classification_result_list[0].classifications[0]
                        score_sum = sum(
                            category.score
                            for category in classification.categories
                            if category.category_name in ["Hands", "Clapping", "Cap gun"]
                        )
                        score_sum -= sum(
                            category.score
                            for category in classification.categories
                            if category.category_name == "Finger snapping"
                        )
                        
                        # Envoi de tous les labels et scores détectés
                        top3_labels = sorted(classification.categories, key=lambda x: x.score, reverse=True)[:3]
                        top3_labels_json = [{"label": label.category_name, "score": label.score} for label in top3_labels]
                        
                        # Log pour debug
                        logging.info(f"Labels détectés: {top3_labels_json}")
                        
                        # Émettre les labels via socketio
                        if _socketio:
                            _socketio.emit("labels", {"detected": top3_labels_json})

                        if score_sum > score_threshold:
                            current_time = time.time()
                            if current_time - last_clap_time > delay:
                                logging.info(f"CLAP détecté sur la source VBAN {vban_ip} avec score {score_sum}")
                                try:
                                    # Émettre l'événement avec plus d'informations
                                    if _socketio:
                                        _socketio.emit('clap', {
                                            'source_id': f'vban-{vban_ip}',
                                            'timestamp': current_time,
                                            'score': float(score_sum)
                                        })
                                    
                                    # Appel webhook si configuré
                                    if webhook_url:
                                        response = requests.post(webhook_url)
                                        logging.info(f"Webhook VBAN appelé: {response.status_code}")
                                except Exception as e:
                                    logging.error(f"Erreur lors de l'émission de l'événement clap VBAN: {str(e)}")
                                    
                                last_clap_time = current_time
                                
                        # Clear results after processing
                        classification_result_list.clear()
                        
                except Exception as e:
                    logging.error(f"Erreur dans le callback VBAN: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
            
            def source_callback(sources):
                logging.info(f"Sources VBAN actives : {list(sources.keys())}")
            
            detector.source_callback = source_callback
            detector.set_audio_callback(audio_callback)
            detector.start_listening()
            return True  # Pour les sources VBAN, on retourne directement car le traitement est asynchrone
        else:
            logging.info("Microphone")
            try:
                # Recharger les paramètres pour avoir le dernier device_index
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                microphone_settings = settings.get('microphone', {})
                device_index = int(microphone_settings.get('device_index', 0))
                logging.info(f"Utilisation du microphone avec device_index: {device_index}")
                
                record = sd.InputStream(
                    samplerate=sample_rate, 
                    channels=num_channels, 
                    device=device_index
                )
                record.start()
            except Exception as e:
                logging.error(f"Erreur lors de l'initialisation du microphone: {str(e)}")
                return False

        while detection_running:
            now = time.time()
            diff = now - last_inference_time
            if diff < interval_between_inference:
                time.sleep(pause_time)
                continue
            last_inference_time = now

            try:
                if audio_source.startswith("rtsp"):
                    audio_data_array = next(rtsp_reader)
                    if audio_data_array is None:
                        break
                    audio_data.load_from_array(audio_data_array)
                else:  # Microphone
                    data, _ = record.read(buffer_size)
                    data = data.reshape(-1, 1)
                    audio_data.load_from_array(data)

                classifier.classify_async(audio_data, round(time.time() * 1000))

                if classification_result_list:
                    classification = classification_result_list[0].classifications[0]
                    score_sum = sum(
                        category.score
                        for category in classification.categories
                        if category.category_name in ["Hands", "Clapping", "Cap gun"]
                    )
                    score_sum -= sum(
                        category.score
                        for category in classification.categories
                        if category.category_name == "Finger snapping"
                    )

                    # Envoi de tous les labels et scores détectés
                    top3_labels = sorted(classification.categories, key=lambda x: x.score, reverse=True)[:3]
                    top3_labels_json = [{"label": label.category_name, "score": label.score} for label in top3_labels]
                    if _socketio:
                        _socketio.emit("labels", {"detected": top3_labels_json})

                    if score_sum > score_threshold:
                        current_time = time.time()
                        if current_time - last_clap_time > delay:
                            source_id = 'microphone'
                            if audio_source.startswith("rtsp"):
                                source_id = f'rtsp-{rtsp_url}'

                            logging.info(f"CLAP détecté sur la source {source_id}")
                            try:
                                if _socketio:
                                    _socketio.emit('clap', {
                                        'source_id': source_id,
                                        'timestamp': current_time,
                                        'score': float(score_sum)
                                    })
                                
                                if webhook_url:
                                    response = requests.post(webhook_url)
                                    logging.info(f"Webhook appelé: {response.status_code}")
                            except Exception as e:
                                logging.error(f"Erreur lors de l'émission de l'événement clap: {str(e)}")
                                
                            last_clap_time = current_time
                    classification_result_list.clear()

            except Exception as e:
                logging.error(f"Erreur pendant la détection: {str(e)}")
                continue

        stop_detection()
        return True

    except Exception as e:
        logging.error(f"Erreur dans le thread de détection: {e}")
        stop_detection()
        return False

def stop_detection():
    """Arrête la détection"""
    global detection_running, classifier, record, current_audio_source, _socketio
    
    try:
        detection_running = False
        
        # Cleanup VBAN detector if it exists
        detector = get_vban_detector()
        if detector:
            detector.cleanup()
            
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
