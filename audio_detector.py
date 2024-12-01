import numpy as np
import collections
import threading
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.components import containers
from mediapipe.tasks.python.audio import audio_classifier
import mediapipe as mp
import time
import logging

class AudioDetector:
    def __init__(self, model_path, sample_rate=16000, buffer_duration=1.0):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.buffer_size = int(buffer_duration * sample_rate)
        self.sources = {}  # Dict pour stocker les buffers et callbacks par source
        self.source_ids = {}  # Dict pour mapper les noms de source aux IDs numériques
        self.next_source_id = 1  # Commencer à 1 pour éviter les problèmes avec 0
        self.classifier = None
        self.running = False
        self.lock = threading.Lock()
        self.last_detection_time = {}  # Dict pour stocker le dernier temps de détection par source
        self.last_timestamp_ms = {}  # Dict pour stocker le dernier timestamp par source
        self.start_time_ms = None
        self.current_source_id = None  # Pour suivre la source actuelle dans le callback

    def initialize(self, max_results=5, score_threshold=0.3):
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
            logging.info(f"Options du classificateur: max_results={max_results}, score_threshold={score_threshold}")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation du classificateur: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            raise
        
    def add_source(self, source_id, detection_callback=None, labels_callback=None):
        """Ajoute une nouvelle source audio avec ses callbacks"""
        with self.lock:
            # Attribuer un ID numérique à la source
            numeric_id = self.next_source_id
            self.next_source_id += 1
            self.source_ids[source_id] = numeric_id
            
            self.sources[source_id] = {
                'buffer': collections.deque(maxlen=self.buffer_size),
                'detection_callback': detection_callback,
                'labels_callback': labels_callback,
                'numeric_id': numeric_id
            }
            self.last_detection_time[source_id] = 0
            self.last_timestamp_ms[source_id] = 0
            logging.info(f"Source audio ajoutée: {source_id} (ID interne: {numeric_id})")

    def remove_source(self, source_id):
        """Supprime une source audio"""
        with self.lock:
            if source_id in self.sources:
                numeric_id = self.sources[source_id]['numeric_id']
                del self.source_ids[source_id]
                del self.sources[source_id]
                del self.last_detection_time[source_id]
                del self.last_timestamp_ms[source_id]
                logging.info(f"Source audio supprimée: {source_id} (ID interne: {numeric_id})")

    def _handle_result(self, result, timestamp):
        """Gère les résultats de classification"""
        try:
            if not result or not result.classifications or not self.current_source_id:
                return
                
            classification = result.classifications[0]
            source_id = self.current_source_id
            
            # Log pour déboguer les résultats bruts
            logging.debug(f"Résultats bruts pour source {source_id}:")
            for category in classification.categories:
                if category.score > 0.1:  # Abaisser le seuil pour voir plus de résultats
                    logging.debug(f"  - {category.category_name}: {category.score}")
            
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
            
            # Log du score calculé
            if score_sum > 0.1:  # Abaisser le seuil pour le debug
                logging.debug(f"Score de clap calculé pour source {source_id}: {score_sum}")
            
            # Préparer les labels pour le callback
            top3_labels = sorted(
                classification.categories,
                key=lambda x: x.score,
                reverse=True
            )[:3]
            labels_data = [
                {"label": label.category_name, "score": float(label.score)}
                for label in top3_labels
                if label.score > 0.5
            ]
            
            # Log pour déboguer les labels
            logging.debug(f"Labels détectés pour source {source_id}: {labels_data}")
            
            # Envoyer les labels si un callback est défini
            if self.sources[source_id]['labels_callback'] and labels_data:
                try:
                    self.sources[source_id]['labels_callback'](labels_data)
                except Exception as e:
                    logging.error(f"Erreur dans le callback des labels pour source {source_id}: {str(e)}")
            
            # Vérifier si on a détecté un clap
            current_time = time.time()
            if score_sum > 0.3 and (current_time - self.last_detection_time.get(source_id, 0)) > 1.0:
                if self.sources[source_id]['detection_callback']:
                    try:
                        self.sources[source_id]['detection_callback']({
                            'timestamp': current_time,
                            'score': float(score_sum),
                            'source_id': source_id
                        })
                    except Exception as e:
                        logging.error(f"Erreur dans le callback de détection pour source {source_id}: {str(e)}")
                self.last_detection_time[source_id] = current_time
                
        except Exception as e:
            logging.error(f"Erreur dans le traitement du résultat: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

    def process_audio(self, audio_data, source_id):
        """Traite les données audio pour une source spécifique"""
        try:
            if source_id not in self.sources:
                logging.warning(f"Source inconnue: {source_id}")
                return

            # Vérifier si le classificateur est actif
            if not self.running:
                logging.warning("Le classificateur n'est pas actif, démarrage...")
                self.start()
                if not self.running:
                    logging.error("Impossible de démarrer le classificateur")
                    return

            # Rééchantillonnage si nécessaire
            if len(audio_data) > self.buffer_size:
                resampled_data = audio_data[::3]
                audio_data = resampled_data
            
            # S'assurer que les données sont en float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Log des statistiques audio
            if len(audio_data) > 0:
                logging.debug(f"Audio stats (source {source_id}) - min: {np.min(audio_data):.4f}, max: {np.max(audio_data):.4f}, mean: {np.mean(audio_data):.4f}, std: {np.std(audio_data):.4f}")
            
            # Ajouter les nouvelles données au buffer de la source
            self.sources[source_id]['buffer'].extend(audio_data)
            
            # Traiter avec le classificateur
            if self.running and self.classifier and self.start_time_ms is not None:
                block_size = 1600
                buffer_array = np.array(list(self.sources[source_id]['buffer']))
                
                blocks_processed = 0  # Compteur pour le debug
                while len(buffer_array) >= block_size:
                    block = buffer_array[:block_size]
                    buffer_array = buffer_array[block_size:]
                    blocks_processed += 1
                    
                    # Vérifier les statistiques du bloc avant classification
                    block_max = np.max(np.abs(block))
                    if block_max > 0.1:  # Seulement log les blocs avec du son significatif
                        logging.debug(f"Classification d'un bloc audio (source {source_id}) - amplitude max: {block_max:.4f}")
                    
                    audio_data_container = containers.AudioData.create_from_array(
                        block,
                        self.sample_rate
                    )
                    
                    # Calculer le prochain timestamp
                    block_duration_ms = int((block_size / self.sample_rate) * 1000)
                    next_timestamp = max(
                        self.last_timestamp_ms.get(source_id, 0) + block_duration_ms,
                        int(time.time() * 1000)
                    )
                    self.last_timestamp_ms[source_id] = next_timestamp
                    
                    # Définir la source actuelle pour le callback
                    self.current_source_id = source_id
                    
                    # Log avant la classification
                    if block_max > 0.1:
                        logging.debug(f"Envoi au classificateur - source: {source_id}, timestamp: {next_timestamp}")
                    
                    # Classifier le bloc
                    try:
                        self.classifier.classify_async(audio_data_container, next_timestamp)
                    except Exception as e:
                        logging.error(f"Erreur lors de la classification: {str(e)}")
                
                if blocks_processed > 0:
                    logging.debug(f"Blocs traités pour {source_id}: {blocks_processed}")
                
                # Mettre à jour le buffer avec les données restantes
                self.sources[source_id]['buffer'].clear()
                if len(buffer_array) > 0:
                    self.sources[source_id]['buffer'].extend(buffer_array)
            
        except Exception as e:
            logging.error(f"Erreur dans le traitement audio: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def start(self):
        """Démarre la détection"""
        if not self.classifier:
            self.initialize()
        
        # Réinitialiser les timestamps
        self.start_time_ms = int(time.time() * 1000)
        for source_id in self.sources:
            self.last_timestamp_ms[source_id] = self.start_time_ms
        
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
                self.running = True
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
