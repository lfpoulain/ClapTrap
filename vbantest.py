import socket
import pyaudio
import numpy as np
import struct
from scipy import signal

# Configuration VBAN
VBAN_PORT = 6980  # Port standard VBAN
BUFFER_SIZE = 1024 * 4
VBAN_HEADER_SIZE = 28

class VBANHeader:
    def __init__(self, data):
        # Vérifie la signature 'VBAN'
        if data[:4] != b'VBAN':
            raise ValueError("Invalid VBAN packet")
        
        # Décode l'en-tête
        self.protocol = data[4] & 0xE0
        self.sample_rate_index = data[4] & 0x1F
        self.samples_per_frame = data[5]
        self.nb_channels = (data[6] & 0x1F) + 1
        self.data_format = data[7] >> 5
        
        # Table des taux d'échantillonnage VBAN
        sr_table = [6000, 12000, 24000, 48000, 96000, 192000, 384000, 8000, 16000,
                   32000, 64000, 128000, 256000, 512000, 11025, 22050, 44100, 88200,
                   176400, 352800, 705600]
        
        self.sample_rate = sr_table[self.sample_rate_index]

def setup_vban_receiver():
    # Création du socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', VBAN_PORT))
    return sock

def main():
    print("Démarrage du récepteur VBAN...")
    sock = setup_vban_receiver()
    audio = pyaudio.PyAudio()
    stream = None
    header = None

    try:
        print("En attente d'une source VBAN...")
        while True:
            # Réception des données
            data, addr = sock.recvfrom(BUFFER_SIZE)
            
            try:
                # Décodage de l'en-tête VBAN si pas encore fait
                if header is None:
                    header = VBANHeader(data)
                    print(f"Source VBAN détectée - {addr[0]}:{addr[1]}")
                    print(f"Format: {header.sample_rate}Hz, {header.nb_channels} canaux")
                    
                    # Initialisation du flux audio
                    stream = audio.open(
                        format=pyaudio.paFloat32,
                        channels=header.nb_channels,
                        rate=header.sample_rate,
                        output=True
                    )

                # Extraction et lecture des données audio
                audio_data = data[VBAN_HEADER_SIZE:]
                # Conversion en float32 (le format VBAN utilise des int16)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Rééchantillonnage si nécessaire (le détecteur attend du 16kHz)
                if header.sample_rate != 16000:
                    samples = len(audio_array)
                    new_samples = int(samples * 16000 / header.sample_rate)
                    audio_array = signal.resample(audio_array, new_samples)
                
                stream.write(audio_array.tobytes())

            except Exception as e:
                print(f"Erreur: {e}")
                continue

    except KeyboardInterrupt:
        print("\nArrêt du récepteur...")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()
        sock.close()

if __name__ == "__main__":
    main()