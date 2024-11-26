import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { getCurrentSettings } from './settings.js';
import { getSocket } from './socket.js';

let isDetecting = false;

export async function startDetection() {
    try {
        const settings = getCurrentSettings();
        const response = await callApi('/api/detection/start', 'POST', settings);
        if (response.success) {
            isDetecting = true;
            updateDetectionUI(true);
            setupSocketListeners();
            showSuccess('Détection démarrée');
        }
    } catch (error) {
        showError('Erreur lors du démarrage de la détection');
        console.error('Start detection error:', error);
    }
}

export async function stopDetection() {
    try {
        const response = await callApi('/api/detection/stop', 'POST');
        if (response.success) {
            isDetecting = false;
            updateDetectionUI(false);
            removeSocketListeners();
            showSuccess('Détection arrêtée');
            clearDetectionDisplay();
        }
    } catch (error) {
        showError('Erreur lors de l\'arrêt de la détection');
        console.error('Stop detection error:', error);
    }
}

function updateDetectionUI(isActive) {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const labelsContainer = document.getElementById('detected_labels');
    
    if (startButton && stopButton) {
        startButton.style.display = isActive ? 'none' : 'block';
        stopButton.style.display = isActive ? 'block' : 'none';
    }

    if (labelsContainer) {
        labelsContainer.style.display = isActive ? 'block' : 'none';
    }
}

function setupSocketListeners() {
    const socket = getSocket();
    if (socket) {
        socket.on('detection_event', handleDetectionEvent);
        socket.on('clap_detected', handleClapDetection);
    }
}

function removeSocketListeners() {
    const socket = getSocket();
    if (socket) {
        socket.off('detection_event', handleDetectionEvent);
        socket.off('clap_detected', handleClapDetection);
    }
}

function handleDetectionEvent(data) {
    const display = document.getElementById('detection_display');
    const labelsContainer = document.getElementById('detected_labels');
    
    if (display) {
        display.textContent = data.label;
    }

    if (labelsContainer) {
        // Ajouter le nouveau label au début de la liste
        const labelElement = document.createElement('p');
        labelElement.textContent = `${new Date().toLocaleTimeString()} - ${data.label}`;
        
        if (data.label.toLowerCase().includes('clap')) {
            labelElement.classList.add('clap-label');
        }
        
        labelsContainer.insertBefore(labelElement, labelsContainer.firstChild);
        
        // Limiter le nombre de labels affichés
        while (labelsContainer.children.length > 50) {
            labelsContainer.removeChild(labelsContainer.lastChild);
        }
    }
}

function handleClapDetection(data) {
    const display = document.getElementById('detection_display');
    if (display) {
        display.classList.add('clap');
        setTimeout(() => display.classList.remove('clap'), 1000);
    }

    // Afficher l'icône de clap
    showClapIcon();
}

function showClapIcon() {
    const clapIcon = document.createElement('div');
    clapIcon.className = 'clap-icon';
    clapIcon.innerHTML = '👏';
    document.body.appendChild(clapIcon);

    // Animer l'icône
    requestAnimationFrame(() => {
        clapIcon.classList.add('active');
    });

    // Supprimer l'icône après l'animation
    setTimeout(() => {
        clapIcon.remove();
    }, 1000);
}

function clearDetectionDisplay() {
    const display = document.getElementById('detection_display');
    const labelsContainer = document.getElementById('detected_labels');
    
    if (display) {
        display.textContent = '';
        display.classList.remove('clap');
    }
    
    if (labelsContainer) {
        labelsContainer.innerHTML = '';
    }
} 