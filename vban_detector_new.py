import socket
import struct
import time
from collections import defaultdict
import numpy as np
import sounddevice as sd
import scipy.signal
import collections
import threading
import logging
import json

class VBANDetector:
    def __init__(self, port=6980):
        self.port = port
        self.sources = defaultdict(lambda: {'last_seen': 0, 'name': '', 'sample_rate': 0, 'channels': 0})
        self.running = False
        self._socket = None
        self.audio_callback = None
        self.source_callback = None
        self.target_sample_rate = 16000  # Taux d'échantillonnage cible
        
        # Buffer circulaire avec une capacité de 1 seconde au taux d'échantillonnage cible
        self.buffer = collections.deque(maxlen=self.target_sample_rate)
        
        self.last_timestamp = 0
        self.stream = None
        self._lock = threading.Lock()  # Verrou pour la thread-safety
        self._settings_lock = threading.Lock()  # Verrou pour les paramètres
        self._settings_cache = None
        self._last_settings_load = 0
        self._settings_cache_duration = 5  # Durée du cache en secondes
        
    def start_listening(self):
        """Démarre l'écoute des flux VBAN"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            
        self.running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.settimeout(0.5)
        logging.info(f"Démarrage de l'écoute VBAN sur le port {self.port}")
        self._socket.bind(('0.0.0.0', self.port))
        
        # Démarrer l'écoute dans un thread séparé
        self._listen_thread = threading.Thread(target=self._listen_loop)
        self._listen_thread.daemon = True
        self._listen_thread.start()

    def _listen_loop(self):
        """Boucle d'écoute des flux VBAN"""
        logging.info("Thread d'écoute VBAN démarré")
        logged_sources = set()
        
        while self.running:
            try:
                data, addr = self._socket.recvfrom(2048)
                
                # Vérifier que le paquet est assez grand pour contenir l'en-tête VBAN (28 bytes)
                if len(data) < 28:
                    logging.warning(f"Paquet trop petit ({len(data)} bytes), ignoré")
                    continue
                    
                source = self._parse_vban_packet(data, addr, logged_sources)
                if source:
                    # Vérifier si la source est activée dans settings.json
                    settings = self._load_settings()
                    if settings and 'saved_vban_sources' in settings:
                        source_enabled = False
                        for saved_source in settings['saved_vban_sources']:
                            if (saved_source['ip'] == source.ip and 
                                saved_source['stream_name'] == source.name and 
                                saved_source.get('enabled', False)):
                                source_enabled = True
                                break
                        
                        if not source_enabled:
                            continue  # Ignorer les sources désactivées
                            
                    try:
                        # Calculer le nombre d'échantillons complets disponibles
                        audio_bytes = data[28:]
                        num_samples = len(audio_bytes) // 2  # 2 bytes par échantillon int16
                        
                        if num_samples == 0:
                            logging.warning("Pas de données audio dans le paquet")
                            continue
                            
                        # N'utiliser que les bytes correspondant à des échantillons complets
                        audio_data = np.frombuffer(audio_bytes[:num_samples*2], dtype=np.int16)
                        
                        # Convertir en float32 et normaliser entre -1 et 1
                        audio_data = audio_data.astype(np.float32) / 32768.0
                        
                        # Convertir en mono si nécessaire
                        if source.channels > 1:
                            # S'assurer que la taille des données est divisible par le nombre de canaux
                            samples_per_channel = len(audio_data) // source.channels
                            audio_data = audio_data[:samples_per_channel * source.channels]
                            audio_data = audio_data.reshape(-1, source.channels)
                            audio_data = np.mean(audio_data, axis=1)
                        
                        # Rééchantillonner uniquement si absolument nécessaire pour YAMNet
                        if source.sample_rate != self.target_sample_rate:
                            # Calculer le nombre d'échantillons après rééchantillonnage
                            target_length = int(len(audio_data) * self.target_sample_rate / source.sample_rate)
                            if target_length > 0:
                                audio_data = scipy.signal.resample(audio_data, target_length)
                        
                        # Log pour debug
                        if audio_data.max() > 0.3 or audio_data.min() < -0.3:  # Augmenté le seuil à 0.3
                            logging.info(f"Son fort détecté sur {addr[0]}, amplitude: min={audio_data.min():.3f}, max={audio_data.max():.3f}")
                        
                        # Ajouter au buffer de manière thread-safe
                        with self._lock:
                            self.buffer.extend(audio_data)
                            
                            # Appeler le callback audio si nous avons assez d'échantillons
                            if self.audio_callback and len(self.buffer) >= self.target_sample_rate:
                                audio_chunk = np.array(list(self.buffer)[:self.target_sample_rate])
                                self.buffer.clear()
                                current_time = time.time()
                                self.audio_callback(audio_chunk, current_time)
                        
                        # Mettre à jour les informations de la source
                        self.sources[addr[0]].update({
                            'last_seen': time.time(),
                            'name': source.name,
                            'sample_rate': source.sample_rate,
                            'channels': source.channels
                        })
                        
                        # Appeler le callback source si défini
                        if self.source_callback:
                            self.source_callback(self.get_active_sources())
                            
                    except Exception as e:
                        logging.error(f"Erreur lors du traitement des données audio: {str(e)}")
                        continue
            except socket.timeout:
                # Nettoyer les sources inactives (plus de 5 secondes)
                current_time = time.time()
                inactive = [ip for ip, info in self.sources.items() 
                          if current_time - info['last_seen'] > 5]
                for ip in inactive:
                    del self.sources[ip]
                    if self.source_callback:
                        self.source_callback(self.get_active_sources())
                    
    def _parse_vban_packet(self, data, addr, logged_sources=None):
        """Parse un paquet VBAN et retourne les informations de la source"""
        try:
            if len(data) >= 28 and data[0:4] == b'VBAN':
                # Extraire les informations du header VBAN
                sr_index = data[4] & 0x1F
                channels = ((data[4] & 0xE0) >> 5) + 1
                name = self.clean_vban_name(data[8:28])
                ip = addr[0]
                port = addr[1]
                
                # Convertir l'index de sample rate en Hz
                sample_rates = {
                    0: 6000, 1: 12000, 2: 24000, 3: 48000, 4: 96000,
                    5: 192000, 6: 384000, 7: 8000, 8: 16000, 9: 32000,
                    10: 64000, 11: 128000, 12: 256000, 13: 512000,
                    14: 11025, 15: 22050, 16: 44100, 17: 88200,
                    18: 176400, 19: 352800
                }
                sample_rate = sample_rates.get(sr_index, 44100)
                
                # Mettre à jour le dictionnaire des sources
                with self._lock:
                    self.sources[ip] = {
                        'last_seen': time.time(),
                        'name': name,
                        'sample_rate': sample_rate,
                        'channels': channels
                    }
                
                # Créer un objet source
                source = type('VBANSource', (), {
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'channels': channels,
                    'sample_rate': sample_rate
                })
                
                # Log si demandé
                if logged_sources is not None and ip not in logged_sources:
                    logging.info(f"Source VBAN détectée: {name} ({ip}), {channels} canaux @ {sample_rate}Hz")
                    logged_sources.add(ip)
                
                # Notifier le callback des sources si défini
                if self.source_callback:
                    try:
                        self.source_callback(ip, name)
                    except Exception as e:
                        logging.error(f"Erreur dans le callback des sources: {e}")
                
                return source
                
        except Exception as e:
            logging.error(f"Erreur lors du parsing du paquet VBAN: {e}")
            return None

    def stop_listening(self):
        """Arrête l'écoute des flux VBAN"""
        self.running = False
        if self._socket:
            self._socket.close()
            
    def get_active_sources(self):
        """Retourne un dictionnaire des sources actives"""
        return dict(self.sources)
        
    def set_audio_callback(self, callback):
        """Définit le callback pour les données audio"""
        self.audio_callback = callback
        
    def set_source_callback(self, callback):
        """Définit le callback pour les changements de sources"""
        self.source_callback = callback
        
    def clean_vban_name(self, raw_name):
        """Nettoie le nom VBAN en retirant les caractères non désirés"""
        if isinstance(raw_name, bytes):
            try:
                end_idx = 0
                for i, byte in enumerate(raw_name):
                    if byte == 0 or not (32 <= byte <= 126):
                        end_idx = i
                        break
                if end_idx > 0:
                    raw_name = raw_name[:end_idx]
                name = raw_name.decode('ascii', errors='ignore')
            except:
                return ""
        else:
            name = str(raw_name)
            
        name = name.strip()
        while name and not (name[-1].isalnum() or name[-1].isspace()):
            name = name[:-1]
            
        return name

    def cleanup(self):
        """Arrête l'écoute et nettoie les ressources"""
        self.running = False
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            except:
                pass
            self._socket = None
        
        # Attendre que le thread d'écoute se termine
        if hasattr(self, '_listen_thread') and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=1.0)

    def get_sources(self, timeout=1.0):
        """Obtient la liste des sources VBAN actives de manière thread-safe
        
        Args:
            timeout (float): Temps maximum d'attente en secondes
            
        Returns:
            list: Liste des sources VBAN actives
        """
        if not self.running or not self._socket:
            return []
            
        active_sources = []
        start_time = time.time()
        
        with self._lock:
            # Nettoyer les sources inactives
            current_time = time.time()
            inactive = [ip for ip, info in self.sources.items() 
                      if current_time - info['last_seen'] > 5]
            for ip in inactive:
                del self.sources[ip]
                
            # Retourner les sources actives
            for ip, info in self.sources.items():
                if current_time - info['last_seen'] <= timeout:
                    active_sources.append({
                        'ip': ip,
                        'name': info['name'],
                        'sample_rate': info['sample_rate'],
                        'channels': info['channels'],
                        'last_seen': info['last_seen'],
                        'port': self.port  # Add the port number
                    })
                    
        return active_sources

    def _load_settings(self):
        """Charge les paramètres de manière thread-safe avec mise en cache"""
        current_time = time.time()
        
        with self._settings_lock:
            # Utiliser le cache s'il est valide
            if (self._settings_cache is not None and 
                current_time - self._last_settings_load < self._settings_cache_duration):
                return self._settings_cache
            
            try:
                with open('settings.json', 'r') as f:
                    self._settings_cache = json.load(f)
                    self._last_settings_load = current_time
                    return self._settings_cache
            except FileNotFoundError:
                self._settings_cache = {}
                self._last_settings_load = current_time
                return {}
            except json.JSONDecodeError:
                logging.error("Erreur lors de la lecture du fichier settings.json")
                self._settings_cache = {}
                self._last_settings_load = current_time
                return {}
