from vban_detector_new import VBANDetector

# Global VBAN detector instance
vban_detector = None

def init_vban_detector():
    """Initialize the VBAN detector"""
    global vban_detector
    try:
        if vban_detector is None:
            vban_detector = VBANDetector()
            print("VBANDetector initialized")
        return True
    except Exception as e:
        print(f"Error initializing VBANDetector: {e}")
        return False

def get_vban_detector():
    """Get the global VBAN detector instance"""
    global vban_detector
    if vban_detector is None:
        init_vban_detector()
    return vban_detector

def cleanup_vban_detector():
    """Clean up VBAN detector resources"""
    global vban_detector
    if vban_detector:
        vban_detector.stop_listening()
        print("Stopping VBAN detector...")
