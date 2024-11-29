import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from scipy.stats import skew, kurtosis

class VBANSignalProcessor:
    def __init__(self, sample_rate=48000):
        """
        Initialise le processeur de signal VBAN.
        
        Args:
            sample_rate (int): Taux d'échantillonnage en Hz (par défaut 48000)
        """
        self.sample_rate = sample_rate
        
    def apply_lowpass_filter(self, audio_data, cutoff_freq, order=4):
        """
        Applique un filtre passe-bas au signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à filtrer
            cutoff_freq (float): Fréquence de coupure en Hz
            order (int): Ordre du filtre (par défaut 4)
            
        Returns:
            numpy.ndarray: Signal audio filtré
        """
        nyquist = self.sample_rate * 0.5
        normalized_cutoff_freq = cutoff_freq / nyquist
        b, a = signal.butter(order, normalized_cutoff_freq, btype='low')
        return signal.filtfilt(b, a, audio_data)
    
    def apply_highpass_filter(self, audio_data, cutoff_freq, order=4):
        """
        Applique un filtre passe-haut au signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à filtrer
            cutoff_freq (float): Fréquence de coupure en Hz
            order (int): Ordre du filtre (par défaut 4)
            
        Returns:
            numpy.ndarray: Signal audio filtré
        """
        nyquist = self.sample_rate * 0.5
        normalized_cutoff_freq = cutoff_freq / nyquist
        b, a = signal.butter(order, normalized_cutoff_freq, btype='high')
        return signal.filtfilt(b, a, audio_data)
    
    def apply_bandpass_filter(self, audio_data, low_cutoff_freq, high_cutoff_freq, order=4):
        """
        Applique un filtre passe-bande au signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à filtrer
            low_cutoff_freq (float): Fréquence de coupure basse en Hz
            high_cutoff_freq (float): Fréquence de coupure haute en Hz
            order (int): Ordre du filtre (par défaut 4)
            
        Returns:
            numpy.ndarray: Signal audio filtré
        """
        nyquist = self.sample_rate * 0.5
        low = low_cutoff_freq / nyquist
        high = high_cutoff_freq / nyquist
        b, a = signal.butter(order, [low, high], btype='band')
        return signal.filtfilt(b, a, audio_data)
    
    def apply_notch_filter(self, audio_data, center_freq, q=30):
        """
        Applique un filtre coupe-bande (notch) au signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à filtrer
            center_freq (float): Fréquence centrale à supprimer en Hz
            q (float): Facteur de qualité du filtre (par défaut 30)
            
        Returns:
            numpy.ndarray: Signal audio filtré
        """
        nyquist = self.sample_rate * 0.5
        freq = center_freq / nyquist
        b, a = signal.iirnotch(freq, q)
        return signal.filtfilt(b, a, audio_data)
    
    def normalize_signal(self, audio_data):
        """
        Normalise le signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à normaliser
            
        Returns:
            numpy.ndarray: Signal audio normalisé
        """
        return audio_data / np.max(np.abs(audio_data))

    def detect_peaks(self, audio_data, height=0.5, distance=None, prominence=0.3):
        """
        Détecte les pics d'amplitude dans le signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à analyser
            height (float): Hauteur minimale des pics (entre 0 et 1)
            distance (int): Distance minimale entre les pics en échantillons
            prominence (float): Proéminence minimale des pics (entre 0 et 1)
            
        Returns:
            tuple: (indices des pics, propriétés des pics)
        """
        if distance is None:
            # Par défaut, distance minimale de 100ms entre les pics
            distance = int(0.1 * self.sample_rate)
            
        # Normaliser le signal pour la détection des pics
        normalized_data = np.abs(audio_data) / np.max(np.abs(audio_data))
        
        # Détecter les pics
        peaks, properties = signal.find_peaks(
            normalized_data,
            height=height,
            distance=distance,
            prominence=prominence
        )
        
        return peaks, properties
        
    def analyze_peaks(self, audio_data, peaks, properties):
        """
        Analyse les caractéristiques des pics détectés.
        
        Args:
            audio_data (numpy.ndarray): Données audio originales
            peaks (numpy.ndarray): Indices des pics détectés
            properties (dict): Propriétés des pics retournées par find_peaks
            
        Returns:
            list: Liste de dictionnaires contenant les caractéristiques de chaque pic
        """
        results = []
        for i, peak_idx in enumerate(peaks):
            peak_info = {
                'index': peak_idx,
                'amplitude': audio_data[peak_idx],
                'normalized_amplitude': properties['peak_heights'][i],
                'prominence': properties['prominences'][i],
                'width': properties['right_bases'][i] - properties['left_bases'][i],
                'left_base': properties['left_bases'][i],
                'right_base': properties['right_bases'][i]
            }
            results.append(peak_info)
        
        return results

    def compute_temporal_features(self, audio_data, frame_length=1024):
        """
        Calcule les caractéristiques temporelles du signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à analyser
            frame_length (int): Longueur de la fenêtre d'analyse
            
        Returns:
            dict: Caractéristiques temporelles du signal
        """
        # Découper le signal en trames
        n_frames = len(audio_data) // frame_length
        frames = np.array_split(audio_data[:n_frames * frame_length], n_frames)
        
        # Calculer les caractéristiques pour chaque trame
        features = {
            'rms': [],           # Root Mean Square (énergie)
            'zcr': [],           # Zero Crossing Rate
            'skewness': [],      # Asymétrie
            'kurtosis': [],      # Aplatissement
            'crest_factor': []   # Facteur de crête
        }
        
        for frame in frames:
            # RMS (Root Mean Square)
            rms = np.sqrt(np.mean(frame**2))
            
            # Zero Crossing Rate
            zcr = np.sum(np.abs(np.diff(np.signbit(frame)))) / (2 * len(frame))
            
            # Skewness (asymétrie)
            sk = skew(frame)
            
            # Kurtosis (aplatissement)
            kurt = kurtosis(frame)
            
            # Crest Factor (facteur de crête)
            crest = np.max(np.abs(frame)) / rms if rms > 0 else 0
            
            features['rms'].append(rms)
            features['zcr'].append(zcr)
            features['skewness'].append(sk)
            features['kurtosis'].append(kurt)
            features['crest_factor'].append(crest)
        
        # Convertir en arrays numpy
        for key in features:
            features[key] = np.array(features[key])
        
        return features
    
    def compute_spectral_features(self, audio_data, frame_length=1024):
        """
        Calcule les caractéristiques spectrales du signal audio.
        
        Args:
            audio_data (numpy.ndarray): Données audio à analyser
            frame_length (int): Longueur de la fenêtre d'analyse
            
        Returns:
            dict: Caractéristiques spectrales du signal
        """
        # Découper le signal en trames
        n_frames = len(audio_data) // frame_length
        frames = np.array_split(audio_data[:n_frames * frame_length], n_frames)
        
        # Fenêtre de Hanning pour l'analyse spectrale
        window = signal.windows.hann(frame_length)
        
        features = {
            'spectral_centroid': [],      # Centre de gravité spectral
            'spectral_bandwidth': [],     # Largeur de bande spectrale
            'spectral_rolloff': [],       # Fréquence de coupure spectrale
            'spectral_flatness': [],      # Platitude spectrale
            'spectral_contrast': []       # Contraste spectral
        }
        
        for frame in frames:
            # Appliquer la fenêtre
            windowed_frame = frame * window
            
            # Calculer le spectre
            spectrum = np.abs(fft(windowed_frame))[:frame_length//2]
            freqs = fftfreq(frame_length, 1/self.sample_rate)[:frame_length//2]
            
            # Normaliser le spectre
            spectrum_norm = spectrum / np.sum(spectrum) if np.sum(spectrum) > 0 else spectrum
            
            # Centroid (centre de gravité spectral)
            centroid = np.sum(freqs * spectrum_norm) if len(spectrum_norm) > 0 else 0
            
            # Bandwidth (largeur de bande)
            bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * spectrum_norm)) if len(spectrum_norm) > 0 else 0
            
            # Rolloff (fréquence de coupure à 85% de l'énergie)
            cumsum = np.cumsum(spectrum)
            rolloff = freqs[np.where(cumsum >= 0.85 * cumsum[-1])[0][0]] if len(cumsum) > 0 else 0
            
            # Flatness (platitude spectrale - ratio moyenne géométrique/arithmétique)
            geometric_mean = np.exp(np.mean(np.log(spectrum + 1e-10)))
            arithmetic_mean = np.mean(spectrum)
            flatness = geometric_mean / arithmetic_mean if arithmetic_mean > 0 else 0
            
            # Contrast (différence entre pics et vallées)
            contrast = np.max(spectrum) - np.min(spectrum)
            
            features['spectral_centroid'].append(centroid)
            features['spectral_bandwidth'].append(bandwidth)
            features['spectral_rolloff'].append(rolloff)
            features['spectral_flatness'].append(flatness)
            features['spectral_contrast'].append(contrast)
        
        # Convertir en arrays numpy
        for key in features:
            features[key] = np.array(features[key])
        
        return features
    
    def analyze_signal(self, audio_data, frame_length=1024):
        """
        Analyse complète du signal audio, combinant caractéristiques temporelles et spectrales.
        
        Args:
            audio_data (numpy.ndarray): Données audio à analyser
            frame_length (int): Longueur de la fenêtre d'analyse
            
        Returns:
            dict: Toutes les caractéristiques du signal
        """
        # Obtenir les caractéristiques temporelles et spectrales
        temporal_features = self.compute_temporal_features(audio_data, frame_length)
        spectral_features = self.compute_spectral_features(audio_data, frame_length)
        
        # Détecter les pics
        peaks, properties = self.detect_peaks(audio_data)
        peak_features = self.analyze_peaks(audio_data, peaks, properties)
        
        # Combiner toutes les caractéristiques
        features = {
            'temporal': temporal_features,
            'spectral': spectral_features,
            'peaks': peak_features
        }
        
        return features
