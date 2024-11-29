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
        self.stream_classifier = None  # Pour le microphone
        self.clip_classifier = None    # Pour le VBAN
        self.running = False
        self.lock = threading.Lock()
        self.last_detection_time = 0
        self.detection_callback = None
        self.labels_callback = None
        
    def initialize(self, max_results=5, score_threshold=0.5):
        """Initialise les classificateurs audio"""
        try:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            
            # Créer le classificateur en mode stream pour le microphone
            stream_options = audio.AudioClassifierOptions(
                base_options=base_options,
                running_mode=audio.RunningMode.AUDIO_STREAM,
                max_results=max_results,
                score_threshold=score_threshold,
                result_callback=self._handle_result
            )
            self.stream_classifier = audio.AudioClassifier.create_from_options(stream_options)
            
            # Créer le classificateur en mode stream pour le VBAN aussi
            vban_options = audio.AudioClassifierOptions(
                base_options=base_options,
                running_mode=audio.RunningMode.AUDIO_STREAM,
                max_results=max_results,
                score_threshold=score_threshold,
                result_callback=self._handle_result
            )
            self.clip_classifier = audio.AudioClassifier.create_from_options(vban_options)
            
            self.running = True
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
                {"label": label.category_name, "score": float(label.score)}
                for label in top3_labels
                if label.score > 0.5  # Ne garder que les labels avec un score > 0.5
            ]
            
            # Log pour debug
            if labels_data:  # Ne logger que si on a des labels pertinents
                logging.debug(f"Labels détectés: {labels_data}")
            
            # Envoyer les labels si un callback est défini
            if self.labels_callback and labels_data:
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
                            'score': float(score_sum)
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
            
            # Traiter avec le classificateur approprié
            if self.running:
                # S'assurer que les données sont en float32
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                # Pour le VBAN (données plus grandes que 1600 échantillons)
                if len(audio_data) > 1600:
                    # Utiliser des blocs de 4000 échantillons pour VBAN
                    block_size = 4000
                    num_blocks = len(audio_data) // block_size
                    for i in range(num_blocks):
                        block = audio_data[i*block_size:(i+1)*block_size]
                        # Créer le conteneur audio
                        audio_data_container = containers.AudioData.create_from_array(
                            block,
                            self.sample_rate
                        )
                        # Classifier le bloc avec le classificateur VBAN
                        if self.clip_classifier:
                            timestamp_ms = int(time.time() * 1000)
                            self.clip_classifier.classify_async(audio_data_container, timestamp_ms)
                else:
                    # Créer le conteneur audio pour le micro
                    audio_data_container = containers.AudioData.create_from_array(
                        audio_data,
                        self.sample_rate
                    )
                    # Classifier les données en mode async pour le micro
                    if self.stream_classifier:
                        timestamp_ms = int(time.time() * 1000)
                        self.stream_classifier.classify_async(audio_data_container, timestamp_ms)
                
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
        if not self.stream_classifier or not self.clip_classifier:
            self.initialize()
        self.running = True
        
    def stop(self):
        """Arrête le classificateur"""
        if self.running:
            try:
                if self.stream_classifier:
                    self.stream_classifier.close()
                if self.clip_classifier:
                    self.clip_classifier.close()
                self.running = False
            except Exception as e:
                logging.error(f"Erreur lors de l'arrêt du classificateur: {str(e)}")

    def __del__(self):
        """Destructeur pour s'assurer que les classificateurs sont bien arrêtés"""
        self.stop()
