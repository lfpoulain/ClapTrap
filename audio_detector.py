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
        self.classifier = None  # Un seul classificateur pour les deux sources
        self.running = False
        self.lock = threading.Lock()
        self.last_detection_time = 0
        self.detection_callback = None
        self.labels_callback = None
        self.last_timestamp_ms = 0  # Pour suivre le dernier timestamp utilisé
        self.start_time_ms = None   # Temps de démarrage pour calculer les timestamps relatifs
        
    def initialize(self, max_results=5, score_threshold=0.5):
        """Initialise le classificateur audio"""
        try:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            
            # Créer un seul classificateur en mode stream
            options = audio.AudioClassifierOptions(
                base_options=base_options,
                running_mode=audio.RunningMode.AUDIO_STREAM,
                max_results=max_results,
                score_threshold=score_threshold,
                result_callback=self._handle_result
            )
            self.classifier = audio.AudioClassifier.create_from_options(options)
            
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
            
            # S'assurer que les données sont en float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Ajouter les nouvelles données au buffer
            self.buffer.extend(audio_data)
            
            # Log pour debug
            logging.debug(f"Audio data - Shape: {audio_data.shape}, dtype: {audio_data.dtype}, min: {np.min(audio_data)}, max: {np.max(audio_data)}")
            
            # Traiter avec le classificateur
            if self.running and self.classifier and self.start_time_ms is not None:
                # Traiter les données par blocs de 1600 échantillons
                block_size = 1600
                buffer_array = np.array(list(self.buffer))
                
                # Tant qu'il y a assez de données dans le buffer
                while len(buffer_array) >= block_size:
                    # Extraire un bloc
                    block = buffer_array[:block_size]
                    buffer_array = buffer_array[block_size:]
                    
                    # Créer le conteneur audio
                    audio_data_container = containers.AudioData.create_from_array(
                        block,
                        self.sample_rate
                    )
                    
                    # Calculer le prochain timestamp relatif au démarrage
                    # S'assurer qu'il est toujours plus grand que le précédent
                    block_duration_ms = int((block_size / self.sample_rate) * 1000)
                    next_timestamp = max(
                        self.last_timestamp_ms + block_duration_ms,
                        int(time.time() * 1000)
                    )
                    self.last_timestamp_ms = next_timestamp
                    
                    # Classifier le bloc avec le nouveau timestamp
                    self.classifier.classify_async(audio_data_container, next_timestamp)
                
                # Mettre à jour le buffer avec les données restantes
                self.buffer.clear()
                if len(buffer_array) > 0:
                    self.buffer.extend(buffer_array)
            
        except Exception as e:
            logging.error(f"Erreur dans le traitement audio: {e}")
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
        
        # Réinitialiser les timestamps
        self.start_time_ms = int(time.time() * 1000)
        self.last_timestamp_ms = self.start_time_ms
        
        # Démarrer le task runner de MediaPipe
        if self.classifier:
            try:
                # Créer un conteneur audio vide pour démarrer le stream
                empty_data = np.zeros(1600, dtype=np.float32)
                audio_data = containers.AudioData.create_from_array(
                    empty_data,
                    self.sample_rate
                )
                # Démarrer le stream avec le timestamp initial
                self.classifier.classify_async(audio_data, self.start_time_ms)
                logging.info("Task runner MediaPipe démarré avec succès")
            except Exception as e:
                logging.error(f"Erreur lors du démarrage du task runner: {e}")
                return False
        
        self.running = True
        return True

    def stop(self):
        """Arrête le classificateur"""
        self.running = False
        if self.classifier:
            try:
                self.classifier.close()
                self.classifier = None
                logging.info("Classificateur audio arrêté")
            except Exception as e:
                logging.error(f"Erreur lors de l'arrêt du classificateur: {e}")
                
    def __del__(self):
        """Destructeur pour s'assurer que les classificateurs sont bien arrêtés"""
        self.stop()
