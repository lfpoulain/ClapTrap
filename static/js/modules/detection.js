import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { getCurrentSettings } from './settings.js';

let socket = io();
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
        }
    } catch (error) {
        showError('Erreur lors de l\'arrêt de la détection');
        console.error('Stop detection error:', error);
    }
}

function updateDetectionUI(isActive) {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    
    if (startButton && stopButton) {
        startButton.style.display = isActive ? 'none' : 'block';
        stopButton.style.display = isActive ? 'block' : 'none';
    }
}

function setupSocketListeners() {
    socket.on('detection_event', handleDetectionEvent);
}

function removeSocketListeners() {
    socket.off('detection_event', handleDetectionEvent);
}

function handleDetectionEvent(data) {
    const display = document.getElementById('detection_display');
    if (display) {
        display.textContent = `Détection: ${data.label}`;
        if (data.label.toLowerCase().includes('clap')) {
            display.classList.add('clap');
            setTimeout(() => display.classList.remove('clap'), 1000);
        }
    }
} 