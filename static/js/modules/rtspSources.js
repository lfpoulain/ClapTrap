import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

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
    div.className = 'list-group-item';
    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <strong>${stream.name || 'Flux RTSP'}</strong>
            </div>
            <div class="source-controls">
                <label class="switch" title="Activer/Désactiver le flux">
                    <input type="checkbox" class="stream-enabled" data-id="${stream.id}" ${stream.enabled ? 'checked' : ''}>
                    <span class="slider round"></span>
                </label>
                <button type="button" class="btn btn-light btn-sm delete-vban-btn" data-id="${stream.id}">
                    <span class="icon" style="color: #dc3545;">❌</span>
                </button>
            </div>
        </div>
        <div class="webhook-input-group mt-2">
            <label class="form-label">URL RTSP</label>
            <input type="url" class="webhook-input rtsp-url" 
                   value="${stream.url}" 
                   data-id="${stream.id}"
                   placeholder="rtsp://votre-camera:port/flux">
        </div>
        <div class="webhook-input-group mt-2">
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
        urlTimeout = setTimeout(() => {
            const updatedStream = { ...stream, url: e.target.value.trim() };
            updateStream(stream.id, updatedStream);
        }, 500);
    });

    // Webhook URL
    const webhookInput = element.querySelector('.webhook-url');
    let webhookTimeout;
    webhookInput.addEventListener('input', (e) => {
        clearTimeout(webhookTimeout);
        webhookTimeout = setTimeout(() => {
            const updatedStream = { ...stream, webhook_url: e.target.value.trim() };
            updateStream(stream.id, updatedStream);
        }, 500);
    });

    // Enabled switch
    const enabledSwitch = element.querySelector('.stream-enabled');
    enabledSwitch.addEventListener('change', (e) => {
        const updatedStream = { ...stream, enabled: e.target.checked };
        updateStream(stream.id, updatedStream);
    });

    // Delete button
    const deleteButton = element.querySelector('.delete-vban-btn');
    deleteButton.addEventListener('click', () => {
        if (confirm('Voulez-vous vraiment supprimer ce flux RTSP ?')) {
            deleteStream(stream.id);
        }
    });
}

function showAddStreamForm() {
    const div = document.createElement('div');
    div.className = 'list-group-item';
    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <strong>Nouveau flux RTSP</strong>
            </div>
        </div>
        <div class="webhook-input-group mt-2">
            <label class="form-label">Nom</label>
            <input type="text" class="webhook-input" id="new-stream-name" 
                   placeholder="Nom du flux">
        </div>
        <div class="webhook-input-group mt-2">
            <label class="form-label">URL RTSP</label>
            <input type="url" class="webhook-input" id="new-stream-url" 
                   placeholder="rtsp://votre-camera:port/flux">
        </div>
        <div class="webhook-input-group mt-2">
            <label class="form-label">URL Webhook</label>
            <input type="url" class="webhook-input" id="new-stream-webhook" 
                   placeholder="https://votre-serveur.com/webhook">
        </div>
        <div class="webhook-input-group mt-2">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="new-stream-enabled" checked>
                <label class="form-check-label">Activer</label>
            </div>
        </div>
        <div class="webhook-actions">
            <button class="btn btn-primary" id="save-new-stream">Ajouter</button>
            <button class="btn btn-secondary" id="cancel-new-stream">Annuler</button>
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
            showSuccess('Flux RTSP supprimé');
        } else {
            throw new Error(response.error || 'Erreur lors de la suppression');
        }
    } catch (error) {
        showError('Erreur lors de la suppression du flux RTSP');
    }
}