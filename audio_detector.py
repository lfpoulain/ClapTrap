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
        with self.lock:
            if not self.running or not self.classifier:
                return
                
            # Convertir en numpy array si ce n'est pas déjà fait
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
                
            # Log des informations sur les données audio
            logging.debug(f"Audio data - Shape: {audio_data.shape}, dtype: {audio_data.dtype}, min: {audio_data.min()}, max: {audio_data.max()}")
                
            # S'assurer que les données sont en float32 et normalisées entre -1 et 1
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if audio_data.max() > 1.0 or audio_data.min() < -1.0:
                    audio_data = audio_data / 32768.0  # Normalisation pour int16
                    logging.debug(f"After normalization - min: {audio_data.min()}, max: {audio_data.max()}")
            
            # Ajouter les données au buffer
            self.buffer.extend(audio_data.flatten())
            
            # Si on a assez de données, les traiter
            if len(self.buffer) >= self.sample_rate:
                try:
                    # Préparer les données pour la classification
                    data = np.array(list(self.buffer))
                    # Assurer que les données sont dans le bon format (samples, 1)
                    data = data.reshape(-1, 1)
                    
                    # Créer le tenseur audio
                    audio_data = containers.AudioData.create_from_array(
                        data,
                        self.sample_rate
                    )
                    
                    # Classifier les données
                    timestamp = round(time.time() * 1000)
                    self.classifier.classify_async(audio_data, timestamp)
                    
                except Exception as e:
                    logging.error(f"Erreur lors de la classification: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
                finally:
                    # Vider le buffer même en cas d'erreur
                    self.buffer.clear()

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
