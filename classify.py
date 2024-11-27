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
from vban_receptor import VBANDetector
from events import send_clap_event, send_labels
import threading

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")
logging.basicConfig(level=logging.INFO)

# Variables globales
detection_running = False
classifier = None
record = None
model = "yamnet.tflite"
output_file = "recorded_audio.wav"
current_audio_source = None  # Nouvelle variable globale

# Charger les paramètres depuis settings.json
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
        
    # Récupérer la source audio depuis la section microphone
    if 'microphone' in settings:
        AUDIO_SOURCE = settings['microphone'].get('audio_source')
    else:
        AUDIO_SOURCE = None
        
    if not AUDIO_SOURCE:
        raise ValueError("La clé 'audio_source' n'est pas définie correctement dans settings.json")
        
    # Récupérer les paramètres globaux
    THRESHOLD = float(settings['global'].get('threshold', 0.5))
    DELAY = float(settings['global'].get('delay', 2))
    CHUNK_DURATION = float(settings['global'].get('chunk_duration', 0.5))
    BUFFER_DURATION = float(settings['global'].get('buffer_duration', 1.0))
    
except FileNotFoundError:
    raise FileNotFoundError("Le fichier settings.json n'existe pas")
except json.JSONDecodeError:
    raise ValueError("Le fichier settings.json est mal formaté")
except KeyError as e:
    raise ValueError(f"La clé {e} est manquante dans settings.json")

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
    global detection_running, classifier, record, current_audio_source
    logging.info("Démarrage de la détection avec sensibilité : %s", score_threshold)
    try:
        if detection_running:
            return True  # Si déjà en cours, considérer comme un succès

        detection_running = True
        current_audio_source = audio_source

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
        if audio_source.startswith("rtsp"):
            if not rtsp_url:
                raise ValueError("RTSP URL must be provided for RTSP audio source.")
            logging.info("RTSP")
            # Utiliser PyAudio pour lire le flux RTSP
            rtsp_reader = read_audio_from_rtsp(rtsp_url, buffer_size)
        elif audio_source.startswith("vban://"):
            # Extraire l'IP du format vban://IP
            vban_ip = audio_source.replace("vban://", "")
            detector = VBANDetector.get_instance()
            
            def audio_callback(audio_data, timestamp):
                # Convertir en format attendu par le classificateur
                audio_data = np.array(audio_data).reshape(-1, 1)
                audio_data = containers.AudioData.create_from_array(
                    audio_data,
                    containers.AudioDataFormat(1, 16000)
                )
                classifier.classify_async(audio_data, round(timestamp * 1000))
            
            detector.set_audio_callback(audio_callback)
            detector.start_listening()
        else:
            logging.info("Microphone")
            record = sd.InputStream(samplerate=sample_rate, channels=num_channels)
            record.start()

        while detection_running:
            now = time.time()
            diff = now - last_inference_time
            if diff < interval_between_inference:
                time.sleep(pause_time)
                continue
            last_inference_time = now

            if audio_source.startswith("rtsp"):
                audio_data_array = next(rtsp_reader)
                if audio_data_array is None:
                    break
                audio_data.load_from_array(audio_data_array)
                classifier.classify_async(audio_data, round(time.time() * 1000))
            else:
                data, _ = record.read(buffer_size)
                data = data.reshape(-1, 1)  # Redimensionner pour correspondre au format attendu
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
                socketio.emit("labels", {"detected": top3_labels_json})

                if score_sum > 0.5:
                    current_time = time.time()
                    if current_time - last_clap_time > delay:
                        logging.info("CLAP")
                        try:
                            # Émettre l'événement avec plus d'informations
                            print("🔔 Émission de l'événement clap")
                            socketio.emit('clap', {
                                'source_id': 'microphone',
                                'timestamp': time.time(),
                                'score': float(score_sum)
                            }, namespace='/')  # Spécifier le namespace
                            print("✅ Événement clap émis")
                            
                            # Appel webhook si configuré
                            if webhook_url:
                                response = requests.post(webhook_url)
                                logging.info(f"Webhook microphone appelé: {response.status_code}")
                        except Exception as e:
                            print(f"❌ Erreur lors de l'émission de l'événement clap: {str(e)}")
                            
                        last_clap_time = current_time
                classification_result_list.clear()

        stop_detection()

    except Exception as e:
        logging.error(f"Erreur dans le thread de détection: {e}")
        stop_detection()

def stop_detection():
    global detection_running, classifier, record, current_audio_source
    
    try:
        if not detection_running:
            return True  # Si déjà arrêté, considérer comme un succès
            
        detection_running = False
        
        if record:
            record.stop()
            record = None
            
        if classifier:
            classifier.close()
            classifier = None

        if current_audio_source and current_audio_source.startswith("vban://"):
            detector = VBANDetector.get_instance()
            detector.stop_listening()

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
