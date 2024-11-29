from vban_detector_new import VBANDetector
import time

# Global VBAN detector instance
vban_detector = None

def init_vban_detector():
    """Initialize the VBAN detector"""
    global vban_detector
    try:
        if vban_detector is None:
            vban_detector = VBANDetector()
            vban_detector.start_listening()
            # Attendre que le socket soit initialisé
            for _ in range(10):  # Attendre jusqu'à 1 seconde
                if vban_detector._socket is not None:
                    print("VBANDetector initialized and listening")
                    return True
                time.sleep(0.1)
            print("Timeout waiting for VBANDetector to initialize")
            return False
        return True
    except Exception as e:
        print(f"Error initializing VBANDetector: {e}")
        return False

def get_vban_detector():
    """Get the global VBAN detector instance"""
    global vban_detector
    if vban_detector is None:
        if not init_vban_detector():
            return None
    return vban_detector

def cleanup_vban_detector():
    """Clean up VBAN detector resources"""
    global vban_detector
    if vban_detector:
        try:
            vban_detector.stop_listening()
            print("Stopping VBAN detector...")
        except Exception as e:
            print(f"Error stopping VBAN detector: {e}")
        vban_detector = None
