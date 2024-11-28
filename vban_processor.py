import time
import logging
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.components import containers
from vban_manager import get_vban_detector
import requests

class VBANAudioProcessor:
    """
    Classe pour gérer le traitement audio des flux VBAN.
    Cette classe s'occupe de la réception, du traitement et de la détection des claps
    dans les flux audio VBAN.
    """
    
    def __init__(self, ip, port, stream_name, webhook_url=None, score_threshold=0.2, delay=1.0):
        """
        Initialise le processeur audio VBAN.
        
        Args:
            ip (str): Adresse IP de la source VBAN
            port (int): Port de la source VBAN
            stream_name (str): Nom du flux VBAN
            webhook_url (str, optional): URL du webhook à appeler lors de la détection d'un clap
            score_threshold (float, optional): Seuil de score pour la détection des claps
            delay (float, optional): Délai minimum entre deux détections de claps
        """
        # Configuration VBAN
        self.ip = ip
        self.port = port
        self.stream_name = stream_name
        self.webhook_url = webhook_url
        
        # Configuration de la détection
        self.score_threshold = score_threshold
        self.delay = delay
        
        # Configuration audio
        self.sample_rate = 16000  # Taux d'échantillonnage standard pour YAMNet
        self.buffer_size = int(0.975 * self.sample_rate)  # ~975ms buffer
        self.audio_format = containers.AudioDataFormat(1, self.sample_rate)  # Mono, 16kHz
        
        # État interne
        self.is_running = False
        self.last_clap_time = 0
        self.classifier = None
        self.detector = None
        self._socketio = None  # Pour les notifications websocket
        
        # Initialisation du classificateur
        self.initialize_classifier()
        
    def initialize_classifier(self):
        """Configure et initialise le classificateur audio YAMNet."""
        try:
            base_options = python.BaseOptions(model_asset_path="yamnet.tflite")
            options = audio.AudioClassifierOptions(
                base_options=base_options,
                running_mode=audio.RunningMode.AUDIO_STREAM,
                max_results=5,
                score_threshold=0.2,
                result_callback=self._classification_callback
            )
            self.classifier = audio.AudioClassifier.create_from_options(options)
            logging.info("Classificateur audio initialisé avec succès")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation du classificateur: {str(e)}")
            raise
            
    def _classification_callback(self, result: audio.AudioClassifierResult, timestamp_ms: int):
        """
        Callback appelé par le classificateur pour chaque résultat.
        
        Args:
            result: Résultat de la classification audio
            timestamp_ms: Timestamp en millisecondes
        """
        try:
            # Calcul du score pour les sons de claps
            score_sum = sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name in ["Hands", "Clapping", "Cap gun"]
            )
            
            # Soustraction du score des faux positifs
            score_sum -= sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name == "Finger snapping"
            )
            
            # Détection et notification des claps
            if score_sum > self.score_threshold:
                current_time = time.time()
                if current_time - self.last_clap_time > self.delay:
                    self.notify_clap(score_sum, current_time)
                    self.last_clap_time = current_time
                    
        except Exception as e:
            logging.error(f"Erreur dans le callback de classification: {str(e)}")
            
    def set_socketio(self, socketio):
        """
        Configure l'instance SocketIO pour les notifications en temps réel.
        
        Args:
            socketio: Instance SocketIO pour les notifications websocket
        """
        self._socketio = socketio
            
    def start(self):
        """Démarre le traitement audio VBAN."""
        try:
            if self.is_running:
                logging.warning("Le processeur audio est déjà en cours d'exécution")
                return False
                
            # Configurer le détecteur VBAN
            self.detector = get_vban_detector()
            if not self.detector:
                raise RuntimeError("Impossible d'initialiser le détecteur VBAN")
                
            # Ajouter notre callback pour le traitement audio
            self.detector.add_callback(self.audio_callback)
            
            self.is_running = True
            logging.info(f"Démarrage du traitement audio VBAN pour {self.stream_name} ({self.ip}:{self.port})")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors du démarrage du traitement audio: {str(e)}")
            return False
            
    def stop(self):
        """Arrête le traitement audio VBAN."""
        if not self.is_running:
            logging.warning("Le processeur audio n'est pas en cours d'exécution")
            return False
            
        try:
            if self.detector:
                self.detector.remove_callback(self.audio_callback)
            self.is_running = False
            logging.info(f"Arrêt du traitement audio VBAN pour {self.stream_name}")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de l'arrêt du traitement audio: {str(e)}")
            return False
            
    def preprocess_audio(self, audio_data):
        """
        Prépare les données audio pour le classificateur.
        
        Args:
            audio_data (numpy.ndarray): Données audio brutes
            
        Returns:
            containers.AudioData: Données audio formatées pour le classificateur
        """
        try:
            # Aplatir si nécessaire (conversion stéréo -> mono)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Ajuster la taille du buffer
            if len(audio_data) > self.buffer_size:
                audio_data = audio_data[:self.buffer_size]
            elif len(audio_data) < self.buffer_size:
                padding = np.zeros(self.buffer_size - len(audio_data))
                audio_data = np.concatenate([audio_data, padding])
            
            # Formater pour le classificateur
            return containers.AudioData.create_from_array(
                audio_data.reshape(-1, 1),
                self.audio_format
            )
            
        except Exception as e:
            logging.error(f"Erreur lors du prétraitement audio: {str(e)}")
            raise
            
    def detect_claps(self, audio_data, timestamp):
        """
        Détecte les claps dans les données audio.
        
        Args:
            audio_data (containers.AudioData): Données audio prétraitées
            timestamp (float): Timestamp des données audio
        """
        try:
            # Classification du signal audio
            result = self.classifier.classify(audio_data)
            
            # Calcul du score pour les sons de claps
            score_sum = sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name in ["Hands", "Clapping", "Cap gun"]
            )
            
            # Soustraction du score des faux positifs
            score_sum -= sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name == "Finger snapping"
            )
            
            # Détection et notification des claps
            if score_sum > self.score_threshold:
                current_time = time.time()
                if current_time - self.last_clap_time > self.delay:
                    self.notify_clap(score_sum, current_time)
                    self.last_clap_time = current_time
                    
        except Exception as e:
            logging.error(f"Erreur lors de la détection des claps: {str(e)}")
            
    def notify_clap(self, score, timestamp):
        """
        Notifie la détection d'un clap via webhook et websocket.
        
        Args:
            score (float): Score de confiance de la détection
            timestamp (float): Timestamp de la détection
        """
        try:
            # Notification websocket
            if self._socketio:
                self._socketio.emit('clap_detected', {
                    'source': 'vban',
                    'stream_name': self.stream_name,
                    'score': score,
                    'timestamp': timestamp
                })
                
            # Notification webhook
            if self.webhook_url:
                try:
                    response = requests.post(self.webhook_url, json={
                        'event': 'clap_detected',
                        'source': 'vban',
                        'stream_name': self.stream_name,
                        'score': score,
                        'timestamp': timestamp
                    }, timeout=1.0)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logging.error(f"Erreur lors de l'appel webhook: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Erreur lors de la notification: {str(e)}")
            
    def _process_vban_stream(self, stream_data):
        """
        Traite les données brutes du flux VBAN.
        
        Args:
            stream_data (bytes): Données brutes du flux VBAN
            
        Returns:
            numpy.ndarray: Données audio décodées
        """
        try:
            # Décodage des données VBAN
            # Le format attendu est PCM 16 bits, mono ou stéréo
            audio_data = np.frombuffer(stream_data, dtype=np.int16)
            
            # Normalisation des données audio
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            return audio_data
            
        except Exception as e:
            logging.error(f"Erreur lors du traitement du flux VBAN: {str(e)}")
            raise
            
    def audio_callback(self, data, timestamp):
        """
        Callback appelé lorsque des données audio sont reçues du flux VBAN.
        
        Args:
            data (numpy.ndarray): Données audio brutes du flux VBAN
            timestamp (float): Timestamp des données
        """
        try:
            # Prétraitement des données audio
            processed_data = self.preprocess_audio(data)
            
            # Détection des claps
            self.detect_claps(processed_data, timestamp)
            
        except Exception as e:
            logging.error(f"Erreur dans le callback audio: {str(e)}")
