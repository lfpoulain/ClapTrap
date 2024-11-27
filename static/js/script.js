import { initAudioSources } from './modules/audioSources.js';
import { initVbanSources, refreshVbanSources } from './modules/vbanSources.js';
import { initRtspSources } from './modules/rtspSources.js';
import { initWebhooks } from './modules/webhooks.js';
import { setupEventListeners } from './modules/events.js';
import { updateSettings } from './modules/settings.js';
import { initializeSocketIO } from './modules/socketHandlers.js';

window.showClap = function(sourceId) {
    console.log('📢 showClap called for sourceId:', sourceId);
    
    const clapEmoji = document.querySelector(`#clap-${sourceId}`);
    const detectionDisplay = document.getElementById('detection_display');
    
    console.log('Looking for emoji with id:', `clap-${sourceId}`);
    console.log('Found emoji element:', clapEmoji);
    
    if (clapEmoji && detectionDisplay) {
        console.log('🎯 Showing clap emoji for source:', sourceId);
        
        // Forcer la visibilité
        clapEmoji.classList.add('visible');
        detectionDisplay.classList.add('clap');
        
        console.log('Updated styles:', {
            classList: clapEmoji.classList,
            displayClassList: detectionDisplay.classList
        });
        
        setTimeout(() => {
            console.log('🔄 Hiding clap emoji for source:', sourceId);
            clapEmoji.classList.remove('visible');
            detectionDisplay.classList.remove('clap');
        }, 1000);
    } else {
        console.warn('❌ Elements not found:', {
            emoji: clapEmoji,
            display: detectionDisplay
        });
    }
};

// Ajouter un log pour vérifier que la fonction est bien attachée à window
console.log('🔍 showClap function attached to window:', typeof window.showClap);

window.updateDetectionState = function(isDetecting) {
    // S'assurer que les labels et emojis restent visibles
    document.querySelectorAll('.source-label, .clap-emoji').forEach(element => {
        element.style.display = 'inline-block';
    });
    
    // Désactiver les inputs mais garder les labels visibles
    document.querySelectorAll('input, select').forEach(element => {
        element.disabled = isDetecting;
    });
};

let detectionActive = false;

async function toggleDetection() {
    try {
        const response = await fetch('/api/detection/toggle', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Detection toggle failed');
        }
        
        detectionActive = !detectionActive;
        updateUIState(detectionActive);
    } catch (error) {
        console.error('Error:', error);
        // Remettre l'UI dans un état cohérent
        detectionActive = false;
        updateUIState(false);
        showError('La détection a échoué. Veuillez réessayer.');
    }
}

function updateUIState(active) {
    const button = document.getElementById('detectionButton');
    button.textContent = active ? 'Arrêter la détection' : 'Démarrer la détection';
    // Désactiver/activer les champs de configuration
    document.querySelectorAll('.config-field').forEach(field => {
        field.disabled = active;
    });
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM fully loaded');
    
    if (window.settings) {
        console.log('📝 Settings loaded:', window.settings);
        updateSettings(window.settings);
    } else {
        console.warn('⚠️ No settings found in window object');
    }
    
    // Log l'état initial des éléments importants
    console.log('Initial DOM state:', {
        detectedLabels: document.getElementById('detected_labels'),
        clapEmojis: document.querySelectorAll('.clap-emoji'),
        sourceLabels: document.querySelectorAll('.source-label')
    });
    
    initAudioSources();
    initVbanSources();
    initRtspSources();
    initWebhooks();
    setupEventListeners();
    
    const socket = initializeSocketIO();
    console.log('✅ Socket.IO initialized');
    
    // Vérifier les éléments DOM
    setTimeout(checkDOMElements, 1000);
    
    // Vérifier à nouveau après 5 secondes pour voir si quelque chose a changé
    setTimeout(checkDOMElements, 5000);
});

function debugSocketIO() {
    console.log('Debugging Socket.IO connection...');
    const socket = io();
    
    // Événements de connexion
    socket.on('connect', () => {
        console.log('Socket.IO: Connected successfully');
        console.log('Socket ID:', socket.id);
    });
    
    // Test d'émission
    setInterval(() => {
        socket.emit('ping');
        console.log('Ping sent');
    }, 5000);
    
    // Réception des événements
    socket.on('pong', () => {
        console.log('Pong received');
    });
}

// Appeler la fonction de debug au chargement
document.addEventListener('DOMContentLoaded', debugSocketIO);

function checkDOMElements() {
    const elements = {
        'clap-microphone': document.getElementById('clap-microphone'),
        'detection_display': document.getElementById('detection_display'),
        'detected_labels': document.getElementById('detected_labels'),
        'all-clap-emojis': Array.from(document.querySelectorAll('.clap-emoji')).map(el => ({
            id: el.id,
            display: el.style.display,
            className: el.className
        }))
    };
    
    console.log('🔍 DOM Elements Check:', elements);
    return elements;
}

