import time
import logging
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.components import containers
from vban_manager import get_vban_detector
from circular_buffer import CircularAudioBuffer
from vban_signal_processor import VBANSignalProcessor

class WebhookManager:
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retry_strategy))
        self.session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    
    def send_webhook(self, url, data):
        """Envoie une requête webhook et retourne la réponse"""
        try:
            response = self.session.post(url, json=data, timeout=5)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Webhook failed: {str(e)}")
            raise

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
        self.peak_threshold = 0.15  # Très bas pour être plus sensible
        self.peak_prominence = 0.1  # Très bas pour détecter plus de pics
        
        # Paramètres pour la détection basée sur les caractéristiques
        self.feature_weights = {
            'temporal': {
                'rms': 0.4,           # Beaucoup plus d'importance à l'amplitude
                'zcr': 0.3,           # Plus d'importance aux transitions
                'crest_factor': 0.3   # Plus d'importance aux pics
            },
            'spectral': {
                'spectral_centroid': 0.0,    # Désactivé
                'spectral_contrast': 0.0,    # Désactivé
                'spectral_flatness': 0.0     # Désactivé
            }
        }
        
        # Configuration audio
        self.sample_rate = 16000  # Taux d'échantillonnage standard pour YAMNet
        self.buffer_size = int(0.975 * self.sample_rate)  # ~975ms buffer
        self.audio_format = containers.AudioDataFormat(1, self.sample_rate)  # Mono, 16kHz
        
        # Processeur de signal
        self.signal_processor = VBANSignalProcessor(sample_rate=self.sample_rate)
        
        # Buffer circulaire pour stocker les échantillons audio
        self.circular_buffer = CircularAudioBuffer(self.buffer_size, channels=1)
        
        # État interne
        self.is_running = False
        self.last_clap_time = 0
        self.classifier = None
        self.detector = None
        self._socketio = None  # Pour les notifications websocket
        
        # Initialisation du classificateur
        self.initialize_classifier()
        
        # Gestionnaire de webhooks
        self.webhook_manager = WebhookManager()
        
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
            
    def evaluate_clap_features(self, features):
        """
        Évalue les caractéristiques du signal pour déterminer s'il s'agit d'un clap.
        
        Args:
            features (dict): Caractéristiques du signal
            
        Returns:
            float: Score entre 0 et 1 indiquant la probabilité d'un clap
        """
        score = 0.0
        
        # Évaluation des caractéristiques temporelles
        temporal = features['temporal']
        if len(temporal['rms']) > 0:
            # Forte amplitude soudaine
            rms_score = np.max(temporal['rms']) * self.feature_weights['temporal']['rms']
            
            # Taux de passage par zéro élevé
            zcr_score = np.mean(temporal['zcr']) * self.feature_weights['temporal']['zcr']
            
            # Facteur de crête élevé (caractéristique des sons impulsifs)
            crest_score = np.max(temporal['crest_factor']) * self.feature_weights['temporal']['crest_factor']
            
            score += rms_score + zcr_score + crest_score
        
        # Évaluation des caractéristiques spectrales
        spectral = features['spectral']
        if len(spectral['spectral_centroid']) > 0:
            # Centre de gravité spectral élevé
            centroid_score = (np.mean(spectral['spectral_centroid']) / (self.sample_rate/4)) * \
                           self.feature_weights['spectral']['spectral_centroid']
            
            # Contraste spectral élevé
            contrast_score = np.max(spectral['spectral_contrast']) * \
                          self.feature_weights['spectral']['spectral_contrast']
            
            # Faible platitude spectrale (son non tonal)
            flatness_score = (1 - np.mean(spectral['spectral_flatness'])) * \
                          self.feature_weights['spectral']['spectral_flatness']
            
            score += centroid_score + contrast_score + flatness_score
        
        return min(score, 1.0)  # Normaliser le score entre 0 et 1

    def _classification_callback(self, result: audio.AudioClassifierResult, timestamp_ms: int):
        """
        Callback appelé par le classificateur pour chaque résultat.
        """
        try:
            # Récupérer les données audio actuelles du buffer
            current_audio = self.circular_buffer.get_buffer()
            
            # Analyser le signal
            signal_features = self.signal_processor.analyze_signal(current_audio)
            
            # Évaluer les caractéristiques pour la détection de claps
            feature_score = self.evaluate_clap_features(signal_features)
            
            # Calcul du score pour les sons de claps (YAMNet)
            yamnet_score = sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name in ["Hands", "Clapping", "Cap gun"]
            )
            
            # Soustraction du score des faux positifs
            yamnet_score -= sum(
                category.score
                for category in result.classifications[0].categories
                if category.category_name == "Finger snapping"
            )
            
            # Combiner les scores (moyenne pondérée)
            combined_score = (yamnet_score * 0.4 + feature_score * 0.6)
            
            # Détection et notification des claps
            if combined_score > self.score_threshold:
                current_time = time.time()
                if current_time - self.last_clap_time > self.delay:
                    self.notify_clap(combined_score, current_time)
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
            self.circular_buffer.clear()  # Vide le buffer à l'arrêt
            logging.info(f"Arrêt du traitement audio VBAN pour {self.stream_name}")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de l'arrêt du traitement audio: {str(e)}")
            return False
            
    def preprocess_audio(self, audio_data):
        """
        Prépare les données audio pour le classificateur.
        Garde le signal brut, fait uniquement la conversion de format nécessaire.
        
        Args:
            audio_data (numpy.ndarray): Données audio brutes
            
        Returns:
            containers.AudioData: Données audio formatées pour le classificateur
        """
        # Convertir en format audio pour le classificateur sans aucun filtrage
        return containers.AudioData.create_from_array(
            audio_data,
            self.audio_format
        )
            
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
                    logging.info(f"Envoi webhook vers {self.webhook_url} pour le stream {self.stream_name}")
                    data = {
                        'event': 'clap_detected',
                        'source': 'vban',
                        'stream_name': self.stream_name,
                        'score': score,
                        'timestamp': timestamp
                    }
                    response = self.webhook_manager.send_webhook(self.webhook_url, data)
                    logging.info(f"Webhook envoyé avec succès, status: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Erreur lors de l'appel webhook pour {self.stream_name}: {str(e)}, URL: {self.webhook_url}")
                    
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
            # Traitement des données VBAN
            audio_data = self._process_vban_stream(data)
            
            # Écriture dans le buffer circulaire
            if not self.circular_buffer.write(audio_data):
                logging.warning("Échec de l'écriture dans le buffer circulaire")
                return
                
            # Lecture du buffer pour le traitement
            processed_data = self.circular_buffer.read(self.buffer_size)
            
            # Prétraitement et classification
            processed_audio = self.preprocess_audio(processed_data)
            if self.classifier:
                timestamp_ms = int(timestamp * 1000)
                self.classifier.classify_async(processed_audio, timestamp_ms)
            
            # Détection de claps si nécessaire
            if self.detector:
                self.detect_claps(processed_audio, timestamp)
            
        except Exception as e:
            logging.error(f"Erreur dans le callback audio: {str(e)}")
