class VBANDetector:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.audio_callback = None
        self.is_listening = False

    def set_audio_callback(self, callback):
        self.audio_callback = callback

    def start_listening(self):
        self.is_listening = True
        # Add VBAN listening implementation here

    def stop_listening(self):
        self.is_listening = False
        # Add VBAN cleanup implementation here 