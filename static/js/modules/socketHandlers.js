import { showNotification, showSuccess, showError } from './notifications.js';

export function initializeSocketIO() {
    const socket = io.connect('http://' + document.domain + ':16045', {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('Connecté au serveur Socket.IO');
        showSuccess('Connecté au serveur');
    });

    socket.on('connect_error', (error) => {
        console.error('Erreur de connexion Socket.IO:', error);
        const startButton = document.getElementById('startButton');
        if (startButton && startButton.style.display !== 'inline-flex') {
            showError('Erreur de connexion au serveur');
        }
    });

    // Gestion des claps
    socket.on('clap', (data) => {
        console.log('Clap détecté:', data);
        
        // Gestion du detection_display
        const display = document.getElementById('detection_display');
        if (display) {
            display.innerHTML = '👏';
            display.classList.add('clap');
            
            setTimeout(() => {
                display.innerHTML = '';
                display.classList.remove('clap');
            }, 1000);
        }

        // Gestion de l'icône clap
        const clapIcon = document.querySelector('.clap-icon');
        if (clapIcon) {
            clapIcon.classList.add('active');
            setTimeout(() => {
                clapIcon.classList.remove('active');
            }, 1000);
        }
    });

    // Gestion des labels
    socket.on('labels', (data) => {
        console.log('Labels reçus:', data);
        const labelsDiv = document.getElementById('detected_labels');
        if (!labelsDiv) {
            console.error('Element detected_labels non trouvé');
            return;
        }

        // S'assurer que le conteneur est visible
        labelsDiv.style.display = 'block';
        
        if (data.detected && Array.isArray(data.detected)) {
            labelsDiv.innerHTML = '';
            
            const sortedLabels = [...data.detected]
                .sort((a, b) => b.score - a.score)
                .slice(0, 5);
            
            sortedLabels.forEach(item => {
                const labelElement = document.createElement('div');
                labelElement.classList.add('label');
                labelElement.textContent = `${item.label} (${Math.round(item.score * 100)}%)`;
                labelsDiv.appendChild(labelElement);
            });
        }
    });

    return socket;
} 