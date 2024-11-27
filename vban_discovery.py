import socket
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class VBANSource:
    ip: str
    port: int
    stream_name: str
    last_seen: float
    sample_rate: int
    channels: int
    
    def to_dict(self):
        """Convertit la source VBAN en dictionnaire pour l'API"""
        return {
            'name': self.stream_name,
            'ip': self.ip,
            'port': self.port,
            'channels': self.channels,
            'sample_rate': self.sample_rate,
            'id': f'vban_{self.ip}_{self.port}'
        }
        
    def update_last_seen(self):
        self.last_seen = time.time()
    
class VBANDiscovery:
    def __init__(self, bind_ip: str = '0.0.0.0', bind_port: int = 6980):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.sources: Dict[str, VBANSource] = {}
        self.running = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        print(f"VBANDiscovery initialisé sur {bind_ip}:{bind_port}")
        
    def start(self):
        if self.running:
            print("VBANDiscovery déjà en cours d'exécution")
            return
        
        try:
            # Fermer le socket existant s'il y en a un
            if self._sock:
                try:
                    self._sock.close()
                except:
                    pass
                self._sock = None
            
            # Créer un nouveau socket
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.settimeout(0.5)  # Timeout de 500ms
            
            # Essayer de lier le socket
            try:
                self._sock.bind((self.bind_ip, self.bind_port))
            except socket.error as e:
                if e.errno == 48:  # Address already in use
                    print(f"Port {self.bind_port} déjà utilisé, tentative de libération...")
                    # Attendre un peu et réessayer
                    time.sleep(1)
                    self._sock.bind((self.bind_ip, self.bind_port))
                else:
                    raise
            
            print(f"Socket VBAN lié à {self.bind_ip}:{self.bind_port}")
            self.running = True
            self._thread = threading.Thread(target=self._discovery_loop)
            self._thread.daemon = True
            self._thread.start()
            print("Boucle de découverte VBAN démarrée")
        except Exception as e:
            print(f"Erreur lors du démarrage de la découverte VBAN: {e}")
            if self._sock:
                try:
                    self._sock.close()
                except:
                    pass
                self._sock = None
            self.running = False
            raise
            
    def stop(self):
        print("Arrêt de la découverte VBAN...")
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except:
                pass
            self._sock = None
        if self._thread:
            try:
                self._thread.join(timeout=1.0)
            except:
                pass
            self._thread = None
        print("Découverte VBAN arrêtée")
            
    def _discovery_loop(self):
        print("Démarrage de la boucle de découverte VBAN...")
        while self.running:
            try:
                data, addr = self._sock.recvfrom(2048)  # Buffer plus grand
                print(f"Données reçues de {addr[0]}:{addr[1]} ({len(data)} bytes)")
                if len(data) >= 4:
                    print(f"Magic bytes: {data[:4]}")
                if self._is_vban_packet(data):
                    print(f"Paquet VBAN reçu de {addr[0]}:{addr[1]}")
                    source = self._parse_vban_packet(data, addr)
                    if source:
                        with self._lock:
                            key = f"{source.ip}:{source.port}_{source.stream_name}"
                            self.sources[key] = source
                            print(f"Source VBAN ajoutée/mise à jour: {source.stream_name} ({source.ip}:{source.port})")
                        self._cleanup_old_sources()
                else:
                    print(f"Paquet non-VBAN reçu de {addr[0]}:{addr[1]}")
            except socket.timeout:
                # Timeout normal, continuer la boucle
                continue
            except Exception as e:
                print(f"Erreur dans la boucle de découverte VBAN: {e}")
                break
        
        print("Arrêt de la boucle de découverte VBAN")
        self.running = False
        if self._sock:
            self._sock.close()
            
    def _is_vban_packet(self, data: bytes) -> bool:
        """Vérifie si le paquet reçu est un paquet VBAN valide"""
        is_valid = len(data) >= 4 and data[:4] == b'VBAN'
        if not is_valid and len(data) >= 4:
            print(f"Paquet invalide reçu, magic bytes: {data[:4]}")
        return is_valid
        
    def _parse_vban_packet(self, data: bytes, addr: tuple, logged_sources: set = None) -> Optional[VBANSource]:
        """Parse un paquet VBAN et extrait les informations de la source"""
        try:
            stream_name = data[8:24].decode('ascii').rstrip('\x00')
            sample_rate = self._decode_sample_rate(data[7])
            channels = data[6] + 1
            
            source_key = f"{addr[0]}:{addr[1]}"
            if logged_sources is None or source_key not in logged_sources:
                print(f"Paquet VBAN parsé: {stream_name}, {channels} canaux @ {sample_rate}Hz")
            
            return VBANSource(
                ip=addr[0],
                port=addr[1],
                stream_name=stream_name,
                last_seen=time.time(),
                sample_rate=sample_rate,
                channels=channels
            )
        except Exception as e:
            print(f"Erreur lors du parsing du paquet VBAN: {e}")
            return None
            
    def _decode_sample_rate(self, index: int) -> int:
        """Décode l'index du sample rate en Hz"""
        rates = [6000, 12000, 24000, 48000, 96000, 192000, 384000,
                8000, 16000, 32000, 64000, 128000, 256000, 512000,
                11025, 22050, 44100, 88200, 176400, 352800]
        if 0 <= index < len(rates):
            return rates[index]
        print(f"Index de sample rate invalide: {index}, utilisation de la valeur par défaut")
        return 48000  # Valeur par défaut
        
    def _cleanup_old_sources(self, max_age: float = 5.0):
        """Supprime les sources qui n'ont pas été vues depuis max_age secondes"""
        current_time = time.time()
        with self._lock:
            old_count = len(self.sources)
            self.sources = {
                key: source for key, source in self.sources.items()
                if (current_time - source.last_seen) <= max_age
            }
            new_count = len(self.sources)
            if old_count != new_count:
                print(f"Nettoyage des sources: {old_count - new_count} source(s) supprimée(s)")
            
    def get_active_sources(self) -> List[VBANSource]:
        """Retourne la liste des sources actives"""
        try:
            with self._lock:
                # S'assurer que self.sources est initialisé
                if not hasattr(self, 'sources'):
                    self.sources = {}
                sources = list(self.sources.values())
                print(f"Sources actives: {len(sources)}")
                for source in sources:
                    print(f"- {source.stream_name} ({source.ip}:{source.port})")
                return sources
        except Exception as e:
            print(f"Erreur dans get_active_sources: {str(e)}")
            return []

# Example d'utilisation
if __name__ == "__main__":
    discovery = VBANDiscovery()
    discovery.start()
    
    try:
        while True:
            sources = discovery.get_active_sources()
            print("\nSources VBAN actives:")
            for source in sources:
                print(f"- {source.stream_name} ({source.ip}:{source.port})")
                print(f"  {source.channels} canaux @ {source.sample_rate}Hz")
            time.sleep(1)
    except KeyboardInterrupt:
        discovery.stop() 