import { showNotification, showSuccess, showError } from './notifications.js';

export function initializeSocketIO() {
    console.log('🔌 Initializing Socket.IO...');
    const socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5
    });
    
    socket.on('connect', () => {
        console.log('🟢 Socket.IO Connected with ID:', socket.id);
    });
    
    // Gestionnaire pour les claps
    socket.on('clap', (data) => {
        console.log('🎯 Clap event received:', data);
        if (typeof window.showClap === 'function') {
            window.showClap(data.source_id);
        } else {
            console.error('❌ showClap function not found in window object');
        }
    });

    // Gestionnaire pour les labels
    socket.on('labels', (data) => {
        console.log('🏷️ Labels received:', data);
        const container = document.getElementById('detected_labels');
        const waitingEmoji = document.getElementById('waiting-emoji');
        
        if (!container) {
            console.error('❌ Labels container not found');
            return;
        }

        // Vérifier si on a détecté une éructation
        if (data.detected && Array.isArray(data.detected)) {
            const burpingDetected = data.detected.some(label => label.label === 'Burping, eructation');
            if (burpingDetected && waitingEmoji) {
                console.log('🤢 Burping detected, changing emoji...');
                waitingEmoji.textContent = '😱';
                setTimeout(() => {
                    waitingEmoji.textContent = '👂';
                }, 2000);
            }
        }

        // Vider le conteneur
        container.innerHTML = '';

        // Ajouter les nouveaux labels
        if (data.detected && Array.isArray(data.detected)) {
            data.detected.forEach(label => {
                const labelElement = document.createElement('span');
                labelElement.className = 'label';
                labelElement.innerHTML = `
                    ${label.label}
                    <span class="label-score">${Math.round(label.score * 100)}%</span>
                `;
                container.appendChild(labelElement);
            });
        }
    });

    return socket;
} 