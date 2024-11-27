import { callApi } from './api.js';
import { showNotification, showSuccess, showError } from './notifications.js';

let vbanSources = [];
let savedVbanSources = [];

export function initVbanSources() {
    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshVbanSources();
        });
    }

    // Charger les sources initiales
    refreshVbanSources();
    // Rafraîchir périodiquement
    setInterval(refreshVbanSources, 10000);
}

export function refreshVbanSources() {
    const detectedSourcesContainer = document.getElementById('detectedVBANSources');
    if (!detectedSourcesContainer) {
        console.error('Container detectedVBANSources non trouvé');
        return;
    }

    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.classList.add('rotating');
    }

    fetch('/api/vban/sources')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(sources => {
            console.log('Sources VBAN reçues:', sources);
            detectedSourcesContainer.innerHTML = '';

            if (!Array.isArray(sources) || sources.length === 0) {
                detectedSourcesContainer.innerHTML = `
                    <div class="list-group-item text-muted">Aucune source VBAN détectée</div>
                `;
                return;
            }

            const template = document.getElementById('vbanDetectedSourceTemplate');
            if (!template) {
                throw new Error('Template vbanDetectedSourceTemplate non trouvé');
            }

            sources.forEach(source => {
                console.log('Traitement de la source:', source);  // Debug log
                const clone = template.content.cloneNode(true);
                
                clone.querySelector('.source-name').textContent = source.name || source.stream_name;
                clone.querySelector('.source-ip').textContent = source.ip;
                clone.querySelector('.source-port').textContent = source.port;
                
                const addButton = clone.querySelector('.add-vban-btn');
                if (addButton) {
                    addButton.setAttribute('data-source-id', source.id);
                    addButton.addEventListener('click', () => {
                        console.log('Ajout de la source:', source);  // Debug log
                        saveVBANSource(source);
                    });
                }

                detectedSourcesContainer.appendChild(clone);
            });
        })
        .catch(error => {
            console.error('Erreur lors de la récupération des sources VBAN:', error);
            detectedSourcesContainer.innerHTML = `
                <div class="list-group-item text-danger">
                    Erreur lors de la récupération des sources VBAN: ${error.message}
                </div>
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
            showSuccess('Source VBAN ajoutée avec succès');
            refreshVbanSources();
        } else {
            throw new Error(data.error || 'Erreur lors de l\'ajout de la source');
        }
    })
    .catch(error => {
        console.error('Erreur lors de la sauvegarde de la source VBAN:', error);
        showError(error.message);
    });
}

// Autres fonctions spécifiques aux sources VBAN... 