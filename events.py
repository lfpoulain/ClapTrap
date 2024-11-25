from flask_socketio import SocketIO

# Instance globale de Socket.IO
socketio = SocketIO()

def send_clap_event():
    """Envoie un événement de clap via Socket.IO"""
    socketio.emit('clap', {'message': 'Applaudissement détecté!'})

def send_labels(labels):
    """Envoie les labels détectés via Socket.IO"""
    socketio.emit('labels', {'detected': labels}) 