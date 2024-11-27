import { showNotification, showSuccess, showError } from './notifications.js';

export function initializeSocketIO() {
    console.log('🔌 Initializing Socket.IO...');
    const socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
        transports: ['websocket', 'polling']
    });
    
    socket.on('connect', () => {
        console.log('🟢 Socket.IO Connected with ID:', socket.id);
        socket.emit('test_connection');
    });
    
    socket.on('clap', (data) => {
        console.log('🎯 Clap event received:', data);
        const sourceId = data.source_id;
        console.log('Source ID:', sourceId);
        
        // Vérifier l'élément avant d'appeler showClap
        const clapEmoji = document.querySelector(`#clap-${sourceId}`);
        console.log('Clap emoji element:', clapEmoji);
        
        if (clapEmoji) {
            console.log('Showing clap emoji');
            window.showClap(sourceId);
        } else {
            console.error('❌ Clap emoji element not found');
            // Log tous les emojis disponibles
            const allEmojis = document.querySelectorAll('.clap-emoji');
            console.log('Available emoji elements:', Array.from(allEmojis));
        }
    });
    
    // Ajouter un gestionnaire pour les messages de debug
    socket.on('debug', (data) => {
        console.log('🔍 Server debug:', data);
    });
    
    return socket;
} 