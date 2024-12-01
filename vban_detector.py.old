import socket
import struct
import time
import sounddevice as sd
import numpy as np
from collections import defaultdict
import scipy.signal
import collections

class VBANDetector:
    _instance = None
    _socket = None
    
    def __init__(self, port=6980):
        self.port = port
        self.sources = defaultdict(lambda: {'last_seen': 0, 'name': '', 'sr': 0, 'channels': 0})
        self.stream = None
        self.first_source_info = None
        self.audio_callback = None
        self.source_callback = None
        self.running = False
        self.buffer = collections.deque(maxlen=48000)  # Buffer 1 seconde à 48kHz
        self.last_timestamp = 0
        self.sample_rate = 16000  # Taux d'échantillonnage cible
        print(f"VBANDetector initialisé sur le port {port}")
    
    @classmethod
    def get_instance(cls, port=6980):
        if cls._instance is None:
            cls._instance = cls(port)
        return cls._instance
    
    def start_listening(self):
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            
        self.running = True
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(0.5)
            self._socket.bind(('0.0.0.0', self.port))
            
            while self.running:
                try:
                    data, addr = self._socket.recvfrom(2048)
                    if len(data) >= 28 and data[0:4] == b'VBAN':
                        raw_name = data[8:28]
                        name = raw_name.split(b'\x00')[0].decode('ascii', errors='ignore').strip()
                        
                        sr_idx = data[4] & 0x1F
                        sample_rates = [6000, 12000, 24000, 48000, 96000, 192000, 384000]
                        sr = sample_rates[sr_idx] if sr_idx < len(sample_rates) else 0
                        channels = (data[6] & 0x1F) + 1
                        
                        source_ip = addr[0]
                        self.sources[source_ip] = {
                            'last_seen': time.time(),
                            'name': name,
                            'sr': sr,
                            'channels': channels
                        }
                        
                except socket.timeout:
                    continue
                
        except Exception as e:
            print(f"Erreur lors de l'écoute VBAN : {e}")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        self.running = False
        if self._socket:
            try:
                self._socket.close()
                self._socket = None
            except:
                pass
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            except:
                pass
    
    def initialize_audio_stream(self, sample_rate, channels):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
        self.stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype=np.float32
        )
        self.stream.start()
    
    def process_audio_data(self, data):
        try:
            print(f"Réception données audio VBAN: {len(data)} bytes")
            # Convertir les données brutes en int16 d'abord (format VBAN standard)
            audio_data = np.frombuffer(data, dtype=np.int16)
            print(f"Données converties en int16: {len(audio_data)} échantillons")
            
            # Normaliser en float32 entre -1 et 1
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Convertir en mono si nécessaire
            if self.first_source_info['channels'] > 1:
                audio_data = audio_data.reshape(-1, self.first_source_info['channels'])
                audio_data = np.mean(audio_data, axis=1)
                print(f"Conversion en mono: {len(audio_data)} échantillons")
            
            # Rééchantillonner si nécessaire
            if self.first_source_info['sr'] != self.sample_rate:
                print(f"Rééchantillonnage de {self.first_source_info['sr']}Hz à {self.sample_rate}Hz")
                ratio = self.sample_rate / self.first_source_info['sr']
                samples_out = int(len(audio_data) * ratio)
                audio_data = scipy.signal.resample_poly(audio_data, self.sample_rate, self.first_source_info['sr'])
            
            # Ajouter au buffer
            self.buffer.extend(audio_data)
            print(f"Buffer actuel: {len(self.buffer)} échantillons")
            
            # Traiter le buffer quand il est assez plein
            if len(self.buffer) >= self.sample_rate:
                print("Traitement du buffer")
                # Extraire un chunk d'une seconde
                audio_chunk = np.array(list(self.buffer)[:self.sample_rate])
                # Retirer les données traitées du buffer
                for _ in range(self.sample_rate):
                    if self.buffer:
                        self.buffer.popleft()
                
                # Créer un timestamp monotone
                current_timestamp = time.time()
                if current_timestamp <= self.last_timestamp:
                    current_timestamp = self.last_timestamp + 0.001
                self.last_timestamp = current_timestamp
                
                # Appeler le callback avec les données et le timestamp
                if self.audio_callback:
                    print("Appel du callback audio")
                    self.audio_callback(audio_chunk, current_timestamp)
                
        except Exception as e:
            print(f"Erreur lors du traitement audio : {e}")
            import traceback
            traceback.print_exc()
    
    def play_audio(self, audio_data):
        self.process_audio_data(audio_data)
    
    def display_active_sources(self):
        current_time = time.time()
        active_sources = {ip: info for ip, info in self.sources.items() 
                         if current_time - info['last_seen'] < 2.0}
        
        print("\nSources VBAN actives :")
        print("-" * 80)
        print(f"{'IP':15} {'Nom':20} {'Sample Rate':12} {'Canaux':8} {'Lecture':8}")
        print("-" * 80)
        
        for ip, info in active_sources.items():
            is_playing = "✓" if self.first_source_info and ip == self.first_source_info['ip'] else ""
            print(f"{ip:15} {info['name']:20} {info['sr']:12} {info['channels']:8} {is_playing:8}")
    
    def get_active_sources(self):
        current_time = time.time()
        active_sources = {}
        
        for ip, info in self.sources.items():
            if current_time - info['last_seen'] < 5.0:
                source_info = info.copy()
                name = source_info.get('name', '').strip()
                
                # Debug
                print(f"Source active - IP: {ip}, Nom original: {name}")
                
                if name:  # Ne garder que les sources avec un nom non vide
                    source_info['name'] = name
                    active_sources[ip] = source_info
        
        return active_sources
    
    def set_audio_callback(self, callback):
        self.audio_callback = callback
        
    def set_source_callback(self, callback):
        self.source_callback = callback
    
    def __del__(self):
        self.stop_listening()
    
    def clean_vban_name(self, raw_name):
        """Nettoie le nom VBAN en retirant les caractères non désirés."""
        # Convertir en string si ce n'est pas déjà fait
        if isinstance(raw_name, bytes):
            try:
                # Trouver la fin du nom (premier octet nul ou non imprimable)
                end_idx = 0
                for i, byte in enumerate(raw_name):
                    if byte == 0 or not (byte >= 32 and byte <= 126):
                        end_idx = i
                        break
                if end_idx > 0:
                    raw_name = raw_name[:end_idx]
                name = raw_name.decode('ascii', errors='ignore')
            except:
                return ""
        else:
            name = str(raw_name)
        
        # Nettoyer le nom
        name = name.strip()
        # Retirer tous les caractères non alphanumériques à la fin du nom
        while name and not (name[-1].isalnum() or name[-1].isspace()):
            name = name[:-1]
        
        return name

if __name__ == "__main__":
    detector = VBANDetector()
    detector.start_listening()

