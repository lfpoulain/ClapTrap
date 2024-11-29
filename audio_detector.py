import numpy as np
import collections
import threading
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.components import containers
import time
import logging

class AudioDetector:
    def __init__(self, model_path, sample_rate=16000, buffer_duration=1.0):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.buffer_size = int(buffer_duration * sample_rate)
        self.buffer = collections.deque(maxlen=self.buffer_size)
        self.classifier = None
        self.running = False
        self.lock = threading.Lock()
        self.last_detection_time = 0
        self.detection_callback = None
        self.labels_callback = None
        
    def initialize(self, max_results=5, score_threshold=0.5):
        """Initialise le classificateur audio"""
        try:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = audio.AudioClassifierOptions(
                base_options=base_options,
                running_mode=audio.RunningMode.AUDIO_STREAM,
                max_results=max_results,
                score_threshold=score_threshold,
                result_callback=self._handle_result
            )
            self.classifier = audio.AudioClassifier.create_from_options(options)
            logging.info(f"Classificateur audio initialisé avec succès (sample_rate: {self.sample_rate}Hz)")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation du classificateur: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            raise
        
    def _handle_result(self, result, timestamp_ms):
        """Gère les résultats de classification"""
        try:
            if not result or not result.classifications:
                return
                
            classification = result.classifications[0]
            
            # Calculer le score pour la détection de clap
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
            
            # Préparer les labels pour le callback
            top3_labels = sorted(
                classification.categories,
                key=lambda x: x.score,
                reverse=True
            )[:3]
            labels_data = [
                {"label": label.category_name, "score": float(label.score)}  # Convertir en float pour la sérialisation JSON
                for label in top3_labels
            ]
            
            # Log pour debug
            logging.debug(f"Labels détectés: {labels_data}")
            
            # Envoyer les labels si un callback est défini
            if self.labels_callback:
                try:
                    self.labels_callback(labels_data)
                except Exception as e:
                    logging.error(f"Erreur dans le callback des labels: {str(e)}")
            
            # Vérifier si on a détecté un clap
            current_time = time.time()
            if score_sum > 0.5 and (current_time - self.last_detection_time) > 1.0:
                if self.detection_callback:
                    try:
                        self.detection_callback({
                            'timestamp': current_time,
                            'score': float(score_sum)  # Convertir en float pour la sérialisation JSON
                        })
                    except Exception as e:
                        logging.error(f"Erreur dans le callback de détection: {str(e)}")
                self.last_detection_time = current_time
                
        except Exception as e:
            logging.error(f"Erreur dans le traitement du résultat: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

    def process_audio(self, audio_data):
        """Traite les données audio"""
        try:
            # Rééchantillonnage si nécessaire
            if len(audio_data) > self.buffer_size:
                # Cas du VBAN à 48000Hz -> 16000Hz
                resampled_data = audio_data[::3]  # Prend 1 échantillon sur 3 pour passer de 48kHz à 16kHz
                audio_data = resampled_data
            
            # Log pour debug
            logging.debug(f"Audio data - Shape: {audio_data.shape}, dtype: {audio_data.dtype}, min: {np.min(audio_data)}, max: {np.max(audio_data)}")
            
            # Traiter avec le classificateur
            if self.classifier:
                # S'assurer que les données sont en float32
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                # Créer le conteneur audio
                audio_data_container = containers.AudioData.create_from_array(
                    audio_data,
                    self.sample_rate
                )
                # Utiliser classify_async pour le mode stream
                timestamp_ms = int(time.time() * 1000)
                self.classifier.classify_async(audio_data_container, timestamp_ms)
                
        except Exception as e:
            logging.error(f"Erreur dans le traitement audio: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
        
    def set_detection_callback(self, callback):
        """Définit le callback pour la détection de claps"""
        self.detection_callback = callback
        
    def set_labels_callback(self, callback):
        """Définit le callback pour les labels détectés"""
        self.labels_callback = callback
        
    def start(self):
        """Démarre la détection"""
        if not self.classifier:
            self.initialize()
        self.running = True
        
    def stop(self):
        """Arrête la détection"""
        self.running = False
        if self.classifier:
            self.classifier.close()
            self.classifier = None
        with self.lock:
            self.buffer.clear()
