import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { saveSettings } from './settings.js';

let rtspStreams = [];

export async function initRtspSources() {
    try {
        rtspStreams = await callApi('/api/rtsp/streams', 'GET');
        setupRtspStreams();
    } catch (error) {
        showError('Erreur lors du chargement des flux RTSP');
    }
}

function setupRtspStreams() {
    const container = document.getElementById('rtspStreamsContainer');
    if (!container) return;

    // Vider le conteneur
    container.innerHTML = '';

    // Ajouter le bouton pour ajouter un nouveau flux
    const addButton = document.createElement('button');
    addButton.className = 'btn btn-primary mb-3';
    addButton.textContent = 'Ajouter un flux RTSP';
    addButton.onclick = showAddStreamForm;
    container.appendChild(addButton);

    // Afficher les flux existants
    rtspStreams.forEach((stream, index) => {
        const streamElement = createStreamElement(stream);
        container.appendChild(streamElement);
    });
}

function createStreamElement(stream) {
    const div = document.createElement('div');
    div.className = 'webhook-card mb-3';
    div.innerHTML = `
        <div class="webhook-header">
            <h4>
                <span class="webhook-icon">📹</span>
                ${stream.name || 'Flux RTSP'}
            </h4>
            <label class="switch" title="Activer/Désactiver le flux">
                <input type="checkbox" class="stream-enabled" data-id="${stream.id}" ${stream.enabled ? 'checked' : ''}>
                <span class="slider round"></span>
            </label>
        </div>
        <div class="webhook-content">
            <div class="webhook-input-group mb-3">
                <label class="form-label">URL RTSP</label>
                <input type="url" class="webhook-input rtsp-url" 
                       value="${stream.url}" 
                       data-id="${stream.id}"
                       placeholder="rtsp://votre-camera:port/flux">
            </div>
            <div class="webhook-input-group">
                <label class="form-label">URL Webhook</label>
                <div class="webhook-input-with-test">
                    <input type="url" class="webhook-input webhook-url" 
                           value="${stream.webhook_url || ''}" 
                           data-id="${stream.id}"
                           placeholder="https://votre-serveur.com/webhook">
                    <button type="button" class="test-webhook" data-source="rtsp-${stream.id}">
                        <span class="icon">🔔</span>
                        Tester
                    </button>
                </div>
            </div>
            <div class="webhook-actions mt-3">
                <button class="btn btn-sm btn-danger delete-stream" data-id="${stream.id}">
                    <span>🗑️</span> Supprimer
                </button>
            </div>
        </div>
    `;

    // Ajouter les écouteurs d'événements
    setupStreamEventListeners(div, stream);

    return div;
}

function setupStreamEventListeners(element, stream) {
    // URL RTSP
    const urlInput = element.querySelector('.rtsp-url');
    let urlTimeout;
    urlInput.addEventListener('input', (e) => {
        clearTimeout(urlTimeout);
        urlTimeout = setTimeout(async () => {
            await updateStream(stream.id, { url: e.target.value.trim() });
        }, 500);
    });

    // Webhook URL
    const webhookInput = element.querySelector('.webhook-url');
    let webhookTimeout;
    webhookInput.addEventListener('input', (e) => {
        clearTimeout(webhookTimeout);
        webhookTimeout = setTimeout(async () => {
            await updateStream(stream.id, { webhook_url: e.target.value.trim() });
        }, 500);
    });

    // Enabled switch
    const enabledSwitch = element.querySelector('.stream-enabled');
    enabledSwitch.addEventListener('change', async (e) => {
        await updateStream(stream.id, { enabled: e.target.checked });
    });

    // Delete button
    const deleteButton = element.querySelector('.delete-stream');
    deleteButton.addEventListener('click', async () => {
        if (confirm('Voulez-vous vraiment supprimer ce flux RTSP ?')) {
            await deleteStream(stream.id);
        }
    });
}

function showAddStreamForm() {
    const div = document.createElement('div');
    div.className = 'webhook-card mb-3';
    div.innerHTML = `
        <div class="webhook-header">
            <h4>
                <span class="webhook-icon">📹</span>
                Nouveau flux RTSP
            </h4>
        </div>
        <div class="webhook-content">
            <div class="webhook-input-group mb-3">
                <label class="form-label">Nom</label>
                <input type="text" class="webhook-input" id="new-stream-name" 
                       placeholder="Nom du flux">
            </div>
            <div class="webhook-input-group mb-3">
                <label class="form-label">URL RTSP</label>
                <input type="url" class="webhook-input" id="new-stream-url" 
                       placeholder="rtsp://votre-camera:port/flux">
            </div>
            <div class="webhook-input-group mb-3">
                <label class="form-label">URL Webhook</label>
                <input type="url" class="webhook-input" id="new-stream-webhook" 
                       placeholder="https://votre-serveur.com/webhook">
            </div>
            <div class="webhook-input-group mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="new-stream-enabled" checked>
                    <label class="form-check-label">Activer</label>
                </div>
            </div>
            <div class="webhook-actions">
                <button class="btn btn-primary" id="save-new-stream">Ajouter</button>
                <button class="btn btn-secondary" id="cancel-new-stream">Annuler</button>
            </div>
        </div>
    `;

    const container = document.getElementById('rtspStreamsContainer');
    container.insertBefore(div, container.firstChild);

    document.getElementById('save-new-stream').onclick = addNewStream;
    document.getElementById('cancel-new-stream').onclick = () => div.remove();
}

async function addNewStream() {
    const name = document.getElementById('new-stream-name').value.trim();
    const url = document.getElementById('new-stream-url').value.trim();
    const webhook_url = document.getElementById('new-stream-webhook').value.trim();
    const enabled = document.getElementById('new-stream-enabled').checked;

    if (!url) {
        showError('L\'URL RTSP est requise');
        return;
    }

    try {
        const response = await callApi('/api/rtsp/stream', 'POST', {
            name,
            url,
            webhook_url,
            enabled
        });

        if (response.success) {
            rtspStreams.push(response.stream);
            setupRtspStreams();
            showSuccess('Flux RTSP ajouté avec succès');
        } else {
            throw new Error(response.error || 'Erreur lors de l\'ajout du flux');
        }
    } catch (error) {
        showError('Erreur lors de l\'ajout du flux RTSP');
    }
}

async function updateStream(streamId, data) {
    try {
        const response = await callApi(`/api/rtsp/stream/${streamId}`, 'PUT', data);
        if (response.success) {
            // Mettre à jour le stream dans la liste locale
            const index = rtspStreams.findIndex(s => s.id === streamId);
            if (index !== -1) {
                rtspStreams[index] = { ...rtspStreams[index], ...data };
            }
            await saveSettings();
            showSuccess('Flux RTSP mis à jour');
        } else {
            throw new Error(response.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        showError('Erreur lors de la mise à jour du flux RTSP');
    }
}

async function deleteStream(streamId) {
    try {
        const response = await callApi(`/api/rtsp/stream/${streamId}`, 'DELETE');
        if (response.success) {
            rtspStreams = rtspStreams.filter(s => s.id !== streamId);
            setupRtspStreams();
            await saveSettings();
            showSuccess('Flux RTSP supprimé');
        } else {
            throw new Error(response.error || 'Erreur lors de la suppression');
        }
    } catch (error) {
        showError('Erreur lors de la suppression du flux RTSP');
    }
}

// RTSP Sources Management Module
export function initRTSPSourcesManager() {
    const addRTSPSourceForm = document.getElementById('add-rtsp-source-form');
    const rtspSourcesList = document.getElementById('rtsp-sources-list');

    function createRTSPSourceElement(source) {
        const sourceElement = document.createElement('div');
        sourceElement.className = 'source-item';
        sourceElement.innerHTML = `
            <div class="source-info">
                <span class="source-name">${source.name}</span>
                <span class="source-details">
                    URL: ${source.url}
                    ${source.webhook_url ? `| Webhook: ${source.webhook_url}` : ''}
                </span>
            </div>
            <div class="source-controls">
                <label class="switch">
                    <input type="checkbox" ${source.enabled ? 'checked' : ''}>
                    <span class="slider round"></span>
                </label>
                <button class="delete-btn">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        const toggleSwitch = sourceElement.querySelector('input[type="checkbox"]');
        toggleSwitch.addEventListener('change', async () => {
            source.enabled = toggleSwitch.checked;
            await updateRTSPSource(source);
        });

        const deleteButton = sourceElement.querySelector('.delete-btn');
        deleteButton.addEventListener('click', async () => {
            await deleteRTSPSource(source);
            sourceElement.remove();
        });

        return sourceElement;
    }

    async function loadRTSPSources() {
        try {
            const response = await fetch('/api/settings');
            const settings = await response.json();
            rtspSourcesList.innerHTML = '';
            settings.rtsp_sources.forEach(source => {
                rtspSourcesList.appendChild(createRTSPSourceElement(source));
            });
        } catch (error) {
            console.error('Error loading RTSP sources:', error);
        }
    }

    async function addRTSPSource(source) {
        try {
            const response = await fetch('/api/rtsp_sources', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(source)
            });
            if (response.ok) {
                rtspSourcesList.appendChild(createRTSPSourceElement(source));
                return true;
            }
            return false;
        } catch (error) {
            console.error('Error adding RTSP source:', error);
            return false;
        }
    }

    async function updateRTSPSource(source) {
        try {
            await fetch('/api/rtsp_sources', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(source)
            });
        } catch (error) {
            console.error('Error updating RTSP source:', error);
        }
    }

    async function deleteRTSPSource(source) {
        try {
            await fetch('/api/rtsp_sources', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(source)
            });
        } catch (error) {
            console.error('Error deleting RTSP source:', error);
        }
    }

    if (addRTSPSourceForm) {
        addRTSPSourceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addRTSPSourceForm);
            const source = {
                name: formData.get('name'),
                url: formData.get('url'),
                webhook_url: formData.get('webhook_url'),
                enabled: true
            };

            if (await addRTSPSource(source)) {
                addRTSPSourceForm.reset();
            }
        });
    }

    // Initial load
    loadRTSPSources();
} 