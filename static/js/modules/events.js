import { startDetection, stopDetection } from './detection.js';
import { refreshVbanSources } from './vbanSources.js';
import { saveSettings } from './settings.js';

export function setupEventListeners() {
    setupDetectionButtons();
    setupRefreshButton();
    setupThresholdControl();
    setupParameterChangeListeners();
}

function setupDetectionButtons() {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');

    if (startButton) {
        startButton.addEventListener('click', async () => {
            // Sauvegarder les paramètres avant de démarrer la détection
            if (await saveSettings()) {
                startDetection();
            }
        });
    }
    
    if (stopButton) {
        stopButton.addEventListener('click', stopDetection);
    }
}

function setupRefreshButton() {
    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshVbanSources);
    }
}

function setupThresholdControl() {
    const threshold = document.getElementById('threshold');
    const thresholdValue = document.getElementById('threshold-value');
    
    if (threshold && thresholdValue) {
        threshold.addEventListener('input', function() {
            thresholdValue.textContent = this.value;
        });
    }
}

function setupParameterChangeListeners() {
    // Écouter les changements sur les champs de paramètres
    const parameterInputs = [
        'threshold',
        'delay',
        'webhook-mic-enabled',
        'webhook-mic-url',
        'micro_source'
    ];

    parameterInputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', async () => {
                await saveSettings();
            });
        }
    });
} 