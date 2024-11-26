import socket
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class VBANSource:
    ip: str
    port: int
    stream_name: str
    last_seen: float
    sample_rate: int
    channels: int
    
class VBANDiscovery:
    def __init__(self, bind_ip: str = "0.0.0.0", bind_port: int = 6980):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.sources: Dict[str, VBANSource] = {}
        self.running = False
        self._lock = threading.Lock()
        
    def start(self):
        """Démarre la découverte des sources VBAN"""
        self.running = True
        self._discovery_thread = threading.Thread(target=self._discovery_loop)
        self._discovery_thread.daemon = True
        self._discovery_thread.start()
        
    def stop(self):
        """Arrête la découverte"""
        self.running = False
        if hasattr(self, '_discovery_thread'):
            self._discovery_thread.join()
            
    def _discovery_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.bind_ip, self.bind_port))
        sock.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1436)  # Taille max d'un paquet VBAN
                if self._is_vban_packet(data):
                    source = self._parse_vban_packet(data, addr)
                    if source:
                        with self._lock:
                            key = f"{addr[0]}:{addr[1]}"
                            self.sources[key] = source
            except socket.timeout:
                self._cleanup_old_sources()
                continue
            except Exception as e:
                print(f"Erreur lors de la découverte VBAN: {e}")
                
    def _is_vban_packet(self, data: bytes) -> bool:
        """Vérifie si le paquet reçu est un paquet VBAN valide"""
        return len(data) >= 4 and data[:4] == b'VBAN'
        
    def _parse_vban_packet(self, data: bytes, addr: tuple) -> Optional[VBANSource]:
        """Parse un paquet VBAN et extrait les informations de la source"""
        try:
            # Format du header VBAN (28 bytes)
            # - 'VBAN' (4 bytes)
            # - Protocol version & sample format (1 byte)
            # - Num samples per frame (1 byte)
            # - Num channels (1 byte)
            # - Sample rate index (1 byte)
            # - Stream name (16 bytes)
            # - Frame counter (4 bytes)
            
            stream_name = data[8:24].decode('ascii').rstrip('\x00')
            sample_rate = self._decode_sample_rate(data[7])
            channels = data[6] + 1
            
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
        rates = [6000, 12000, 24000, 48000, 96000, 192000, 384000]
        if 0 <= index < len(rates):
            return rates[index]
        return 48000  # Valeur par défaut
        
    def _cleanup_old_sources(self, max_age: float = 5.0):
        """Supprime les sources qui n'ont pas été vues depuis max_age secondes"""
        current_time = time.time()
        with self._lock:
            self.sources = {
                k: v for k, v in self.sources.items()
                if (current_time - v.last_seen) <= max_age
            }
            
    def get_active_sources(self) -> List[VBANSource]:
        """Retourne la liste des sources actives"""
        with self._lock:
            return list(self.sources.values())

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