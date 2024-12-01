import socket
import struct
import wave
import time
from pydub import AudioSegment
import numpy as np

class VBANEmitter:
    def __init__(self, ip="127.0.0.1", port=6980, stream_name="Stream1"):
        self.ip = ip
        self.port = port
        self.stream_name = stream_name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_counter = 0
        
    def create_vban_header(self, sample_rate, num_samples, num_channels):
        """Crée un header VBAN"""
        # "VBAN" magic bytes
        header = b'VBAN'
        # Protocol version (0x00) + sample format (0x20 for int16)
        header += struct.pack('B', 0x20)
        # Nombre d'échantillons (0-255) et nombre de canaux (1-256)
        header += struct.pack('B', num_samples - 1)
        header += struct.pack('B', num_channels - 1)
        # Taux d'échantillonnage (index)
        sr_index = {
            6000: 0, 12000: 1, 24000: 2, 48000: 3, 96000: 4, 192000: 5,
            384000: 6, 8000: 7, 16000: 8, 32000: 9, 64000: 10, 128000: 11,
            256000: 12, 512000: 13, 11025: 14, 22050: 15, 44100: 16,
            88200: 17, 176400: 18, 352800: 19
        }.get(sample_rate, 16)  # Default to 44100 if not found
        header += struct.pack('B', sr_index)
        # Nom du stream (20 bytes, padded with zeros)
        stream_name_bytes = self.stream_name.encode('ascii')[:20]
        header += stream_name_bytes.ljust(20, b'\x00')
        # Frame counter
        header += struct.pack('<I', self.frame_counter)
        self.frame_counter += 1
        return header

    def play_mp3(self, mp3_file, chunk_size=256):
        """Joue un fichier MP3 via VBAN"""
        # Charger le MP3
        audio = AudioSegment.from_mp3(mp3_file)
        
        # Convertir en array numpy
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        
        # Paramètres audio
        sample_rate = audio.frame_rate
        num_channels = audio.channels
        
        # Envoyer les données par chunks
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i:i + chunk_size]
            if len(chunk) < chunk_size:
                # Padding du dernier chunk si nécessaire
                chunk = np.pad(chunk, ((0, chunk_size - len(chunk)), (0, 0)) if num_channels == 2 
                             else (0, chunk_size - len(chunk)))
            
            # Créer le paquet VBAN
            header = self.create_vban_header(sample_rate, chunk_size, num_channels)
            data = chunk.tobytes()
            packet = header + data
            
            # Envoyer le paquet
            self.socket.sendto(packet, (self.ip, self.port))
            
            # Attendre le temps nécessaire pour maintenir le timing
            time.sleep(chunk_size / sample_rate)

if __name__ == "__main__":
    emitter = VBANEmitter(ip="127.0.0.1", port=6980, stream_name="TestStream")
    emitter.play_mp3("test.mp3")
