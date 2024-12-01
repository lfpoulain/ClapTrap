import socket
import pyaudio
import numpy as np
import struct
from scipy import signal
from audio_detector import AudioDetector
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    
    # Initialiser le détecteur audio une seule fois
    detector = AudioDetector("yamnet.tflite")
    detector.initialize()
    
    def vban_detection_callback(data):
        logging.info(f"CLAP détecté sur VBAN! Source: {data['source_id']}, Score: {data['score']}")
    
    def vban_labels_callback(labels):
        logging.debug(f"Labels VBAN: {labels}")
    
    # Buffer pour accumuler les données audio
    audio_buffer = np.array([], dtype=np.float32)
    CHUNK_SIZE = 1600  # Taille attendue par le classificateur
    
    try:
        print("En attente d'une source VBAN...")
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            if len(data) <= VBAN_HEADER_SIZE:
                continue

            try:
                header = VBANHeader(data)
                audio_data = np.frombuffer(data[VBAN_HEADER_SIZE:], dtype=np.float32)
                
                # Ajouter la source si elle n'existe pas encore
                source_id = f"vban_{addr[0]}"
                if source_id not in detector.sources:
                    detector.add_source(
                        source_id=source_id,
                        detection_callback=vban_detection_callback,
                        labels_callback=vban_labels_callback
                    )
                    logging.info(f"Nouvelle source VBAN détectée: {addr[0]}")
                
                # Rééchantillonnage si nécessaire (le détecteur attend du 16kHz)
                if header.sample_rate != 16000:
                    samples = len(audio_data)
                    new_samples = int(samples * 16000 / header.sample_rate)
                    audio_data = signal.resample(audio_data, new_samples)
                
                # Traiter les données audio
                detector.process_audio(audio_data, source_id)
                
                # Jouer l'audio
                if stream is None:
                    stream = audio.open(
                        format=pyaudio.paFloat32,
                        channels=header.nb_channels,
                        rate=header.sample_rate,
                        output=True
                    )
                stream.write(audio_data.tobytes())

            except Exception as e:
                logging.error(f"Erreur lors du traitement du paquet VBAN: {e}")
                continue

    except KeyboardInterrupt:
        print("\nArrêt du récepteur...")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()
        sock.close()
        detector.stop()  # Arrêter proprement le détecteur

if __name__ == "__main__":
    main()