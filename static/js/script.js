import { initAudioSources, updateAudioSources } from './modules/audioSources.js';
import { initVbanSources, refreshVbanSources } from './modules/vbanSources.js';
import { initRtspSources } from './modules/rtspSources.js';
import { initWebhooks } from './modules/webhooks.js';
import { setupEventListeners } from './modules/events.js';
import { updateSettings } from './modules/settings.js';
import { initializeSocketIO } from './modules/socketHandlers.js';

function updateVBANSources() {
    const detectedSourcesContainer = document.getElementById('detectedVBANSources');
    if (!detectedSourcesContainer) return;

    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.classList.add('rotating');
    }

    fetch('/api/vban/sources')
        .then(response => response.json())
        .then(response => {
            console.log('Réponse API VBAN:', response);
            detectedSourcesContainer.innerHTML = '';
            
            let sources = [];
            if (Array.isArray(response)) {
                sources = response;
            } else if (response && Array.isArray(response.sources)) {
                sources = response.sources;
            }
            
            if (sources.length === 0) {
                detectedSourcesContainer.innerHTML = `
                    <div class="list-group-item text-muted">Aucune source VBAN détectée</div>
                `;
                return;
            }

            const template = document.getElementById('vbanDetectedSourceTemplate');
            sources.forEach(source => {
                console.log('Traitement source:', source);
                const clone = template.content.cloneNode(true);
                
                clone.querySelector('.source-name').textContent = source.name;
                clone.querySelector('.source-ip').textContent = source.ip;
                clone.querySelector('.source-port').textContent = source.port;
                
                const addButton = clone.querySelector('.add-vban-btn');
                addButton.setAttribute('data-source-id', source.id);
                addButton.addEventListener('click', () => {
                    saveVBANSource(source);
                });

                detectedSourcesContainer.appendChild(clone);
            });
        })
        .catch(error => {
            console.error('Erreur détaillée:', error);
            detectedSourcesContainer.innerHTML = `
                <div class="list-group-item text-danger">Erreur lors de la récupération des sources VBAN</div>
            `;
        })
        .finally(() => {
            if (refreshBtn) {
                refreshBtn.classList.remove('rotating');
            }
        });
}

function saveVBANSource(source) {
    fetch('/api/vban/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(source)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateSavedVBANSources();
            showNotification('Source VBAN ajoutée avec succès', 'success');
        } else {
            showNotification('Erreur lors de l\'ajout de la source VBAN', 'error');
        }
    })
    .catch(error => {
        console.error('Erreur lors de la sauvegarde de la source VBAN:', error);
        showNotification('Erreur lors de l\'ajout de la source VBAN', 'error');
    });
}

function showNotification(message, type) {
    const notification = document.getElementById(type);
    if (notification) {
        notification.textContent = message;
        notification.style.display = 'block';
        setTimeout(() => {
            notification.style.display = 'none';
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.settings) {
        updateSettings(window.settings);
    }
    
    initAudioSources();
    initVbanSources();
    initRtspSources();
    initWebhooks();
    setupEventListeners();
    
    // Initialiser Socket.IO
    const socket = initializeSocketIO();
    
    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            updateVBANSources();
        });
    }

    updateVBANSources();
    setInterval(updateVBANSources, 10000);
});

