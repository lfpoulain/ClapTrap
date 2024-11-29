import numpy as np
import threading

class CircularAudioBuffer:
    """
    Buffer circulaire thread-safe pour stocker les échantillons audio.
    Utilise un verrou pour assurer la sécurité des opérations en contexte multi-thread.
    """
    
    def __init__(self, buffer_size, channels=1):
        """
        Initialise le buffer circulaire.
        
        Args:
            buffer_size (int): Taille du buffer en nombre d'échantillons
            channels (int): Nombre de canaux audio (1 pour mono, 2 pour stéréo)
        """
        self.buffer_size = buffer_size
        self.channels = channels
        self.buffer = np.zeros((buffer_size, channels), dtype=np.float32)
        self.write_pos = 0  # Position d'écriture
        self.lock = threading.Lock()  # Verrou pour la thread-safety
        self.filled = 0  # Nombre d'échantillons remplis
        
    def write(self, data):
        """
        Écrit des données dans le buffer de manière circulaire.
        
        Args:
            data (numpy.ndarray): Données audio à écrire
            
        Returns:
            bool: True si l'écriture a réussi, False sinon
        """
        try:
            with self.lock:
                # Assurons-nous que les données sont dans le bon format
                if len(data.shape) == 1:
                    data = data.reshape(-1, 1)
                elif data.shape[1] != self.channels:
                    raise ValueError(f"Les données doivent avoir {self.channels} canaux")
                
                # Nombre d'échantillons à écrire
                n_samples = len(data)
                
                # Si on a plus de données que la taille du buffer,
                # on ne garde que les derniers échantillons
                if n_samples > self.buffer_size:
                    data = data[-self.buffer_size:]
                    self.buffer[:] = data
                    self.write_pos = 0
                    self.filled = self.buffer_size
                    return True
                
                # Première partie : de write_pos jusqu'à la fin du buffer
                space_to_end = self.buffer_size - self.write_pos
                first_part = min(space_to_end, n_samples)
                self.buffer[self.write_pos:self.write_pos + first_part] = data[:first_part]
                
                # Deuxième partie : du début du buffer si nécessaire
                if first_part < n_samples:
                    remaining = n_samples - first_part
                    self.buffer[:remaining] = data[first_part:]
                
                # Mise à jour de la position d'écriture
                old_write_pos = self.write_pos
                self.write_pos = (self.write_pos + n_samples) % self.buffer_size
                
                # Mise à jour du nombre d'échantillons remplis
                old_filled = self.filled
                self.filled = min(old_filled + n_samples, self.buffer_size)
                
                return True
                
        except Exception as e:
            print(f"Erreur lors de l'écriture dans le buffer: {str(e)}")
            return False
            
    def read(self, n_samples):
        """
        Lit les n_samples derniers échantillons du buffer.
        
        Args:
            n_samples (int): Nombre d'échantillons à lire
            
        Returns:
            numpy.ndarray: Données audio lues
        """
        with self.lock:
            if n_samples > self.buffer_size:
                n_samples = self.buffer_size
                
            if self.filled == 0:
                return np.zeros((n_samples, self.channels))
                
            # On ne peut pas lire plus que ce qu'on a écrit
            n_samples = min(n_samples, self.filled)
            
            # Création du buffer de sortie
            result = np.zeros((n_samples, self.channels))
            
            # Calcul de la position de début de lecture
            start_pos = (self.write_pos - n_samples) % self.buffer_size
            
            # Si les données sont contiguës
            if start_pos + n_samples <= self.buffer_size:
                result[:] = self.buffer[start_pos:start_pos + n_samples]
            else:
                # Lecture en deux parties
                first_part = self.buffer_size - start_pos
                result[:first_part] = self.buffer[start_pos:]
                result[first_part:] = self.buffer[:n_samples - first_part]
            
            return result
                
    def clear(self):
        """Vide le buffer."""
        with self.lock:
            self.buffer.fill(0)
            self.write_pos = 0
            self.filled = 0
            
    def get_buffer_level(self):
        """
        Retourne le niveau de remplissage du buffer.
        
        Returns:
            float: Pourcentage de remplissage (0.0 à 1.0)
        """
        with self.lock:
            return self.filled / self.buffer_size
