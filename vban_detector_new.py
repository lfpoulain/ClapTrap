import socket
import struct
import time
from collections import defaultdict
import numpy as np
import sounddevice as sd
import scipy.signal
import collections

class VBANDetector:
    def __init__(self, port=6980):
        self.port = port
        self.sources = defaultdict(lambda: {'last_seen': 0, 'name': '', 'sample_rate': 0, 'channels': 0})
        self.running = False
        self._socket = None
        self.audio_callback = None
        self.source_callback = None
        self.buffer = collections.deque(maxlen=48000)  # Buffer 1 seconde à 48kHz
        self.last_timestamp = 0
        self.target_sample_rate = 16000  # Taux d'échantillonnage cible
        self.stream = None
        
    def start_detection(self):
        """Démarre la détection des sources VBAN"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
                
        self.running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.settimeout(0.5)
        self._socket.bind(('0.0.0.0', self.port))
        
        while self.running:
            try:
                data, addr = self._socket.recvfrom(2048)
                if len(data) >= 28 and data[0:4] == b'VBAN':
                    # Extraire les informations du header VBAN
                    sr_index = data[4] & 0x1F
                    channels = ((data[4] & 0xE0) >> 5) + 1
                    name = self.clean_vban_name(data[8:28])
                    ip = addr[0]
                    
                    # Convertir l'index de sample rate en Hz
                    sample_rates = {
                        0: 6000, 1: 12000, 2: 24000, 3: 48000, 4: 96000,
                        5: 192000, 6: 384000, 7: 8000, 8: 16000, 9: 32000,
                        10: 64000, 11: 128000, 12: 256000, 13: 512000,
                        14: 11025, 15: 22050, 16: 44100, 17: 88200,
                        18: 176400, 19: 352800
                    }
                    sample_rate = sample_rates.get(sr_index, 44100)
                    
                    # Extraire les données audio
                    audio_data = np.frombuffer(data[28:], dtype=np.float32)
                    
                    # Rééchantillonner si nécessaire
                    if sample_rate != self.target_sample_rate:
                        audio_data = scipy.signal.resample(audio_data, 
                            int(len(audio_data) * self.target_sample_rate / sample_rate))
                    
                    # Ajouter au buffer
                    self.buffer.extend(audio_data)
                    
                    # Appeler le callback audio si défini
                    if self.audio_callback and len(self.buffer) >= self.target_sample_rate:
                        audio_chunk = np.array(list(self.buffer)[:self.target_sample_rate])
                        self.buffer.clear()
                        self.audio_callback(audio_chunk)
                    
                    # Mettre à jour les informations de la source
                    self.sources[ip].update({
                        'last_seen': time.time(),
                        'name': name,
                        'sample_rate': sample_rate,
                        'channels': channels
                    })
                    
                    # Appeler le callback source si défini
                    if self.source_callback:
                        self.source_callback(self.get_active_sources())
                    
            except socket.timeout:
                # Nettoyer les sources inactives (plus de 5 secondes)
                current_time = time.time()
                inactive = [ip for ip, info in self.sources.items() 
                          if current_time - info['last_seen'] > 5]
                for ip in inactive:
                    del self.sources[ip]
                    if self.source_callback:
                        self.source_callback(self.get_active_sources())
                    
    def stop_detection(self):
        """Arrête la détection des sources VBAN"""
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
