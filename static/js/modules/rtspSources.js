import { showSuccess, showError } from './notifications.js';

export function initRtspSources() {
    const addButton = document.getElementById('addRTSPBtn');
    const addForm = document.getElementById('rtspAddForm');
    const cancelButton = document.getElementById('cancelRTSPAdd');
    const sourcesList = document.getElementById('rtspSourcesList');
    const addSourceForm = document.getElementById('add-rtsp-source-form');

    if (addButton) {
        addButton.addEventListener('click', () => {
            addForm.style.display = 'block';
            addButton.style.display = 'none';
        });
    }

    if (cancelButton) {
        cancelButton.addEventListener('click', () => {
            addForm.style.display = 'none';
            addButton.style.display = 'block';
            addSourceForm.reset();
        });
    }

    if (addSourceForm) {
        addSourceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addSourceForm);
            const source = {
                name: formData.get('name'),
                url: formData.get('url'),
                webhook_url: formData.get('webhook_url'),
                enabled: true
            };

            try {
                const response = await fetch('/api/rtsp/sources', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(source)
                });

                if (!response.ok) {
                    throw new Error('Erreur lors de l\'ajout de la source RTSP');
                }

                showSuccess('Source RTSP ajoutée avec succès');
                addForm.style.display = 'none';
                addButton.style.display = 'block';
                addSourceForm.reset();
                loadRTSPSources();
            } catch (error) {
                showError(error.message);
            }
        });
    }

    // Gérer les événements pour les sources existantes
    document.addEventListener('click', async (e) => {
        if (e.target.closest('.remove-rtsp-btn')) {
            const card = e.target.closest('.webhook-card');
            const sourceName = card.querySelector('h4').textContent.trim();
            
            try {
                const response = await fetch('/api/rtsp/sources', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: sourceName })
                });

                if (!response.ok) {
                    throw new Error('Erreur lors de la suppression de la source RTSP');
                }

                showSuccess('Source RTSP supprimée avec succès');
                loadRTSPSources();
            } catch (error) {
                showError(error.message);
            }
        }
    });

    // Gérer les changements d'état (enabled/disabled)
    document.addEventListener('change', async (e) => {
        if (e.target.matches('.source-enabled')) {
            const card = e.target.closest('.webhook-card');
            const sourceName = card.querySelector('h4').textContent.trim();
            const enabled = e.target.checked;

            try {
                const response = await fetch('/api/rtsp/sources', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: sourceName,
                        enabled: enabled
                    })
                });

                if (!response.ok) {
                    throw new Error('Erreur lors de la mise à jour de la source RTSP');
                }

                showSuccess(enabled ? 'Source RTSP activée' : 'Source RTSP désactivée');
            } catch (error) {
                showError(error.message);
                e.target.checked = !enabled; // Remettre dans l'état précédent
            }
        }
    });

    // Gérer les changements de webhook URL
    document.addEventListener('change', async (e) => {
        if (e.target.matches('.webhook-url')) {
            const card = e.target.closest('.webhook-card');
            const sourceName = card.querySelector('h4').textContent.trim();
            const webhookUrl = e.target.value.trim();

            try {
                const response = await fetch('/api/rtsp/sources', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: sourceName,
                        webhook_url: webhookUrl
                    })
                });

                if (!response.ok) {
                    throw new Error('Erreur lors de la mise à jour du webhook');
                }

                showSuccess('Webhook mis à jour avec succès');
            } catch (error) {
                showError(error.message);
            }
        }
    });

    // Charger les sources initiales
    loadRTSPSources();
}

async function loadRTSPSources() {
    const sourcesList = document.getElementById('rtspSourcesList');
    if (!sourcesList) return;

    try {
        const response = await fetch('/api/rtsp/sources');
        const sources = await response.json();

        sourcesList.innerHTML = '';
        
        if (!Array.isArray(sources) || sources.length === 0) {
            sourcesList.innerHTML = `
                <div class="list-group-item text-muted">Aucune source RTSP configurée</div>
            `;
            return;
        }

        sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'webhook-card mb-3';
            card.innerHTML = `
                <div class="webhook-header">
                    <h4>
                        <span class="webhook-icon">📹</span>
                        ${source.name}
                    </h4>
                    <label class="switch" title="Activer/Désactiver la source">
                        <input type="checkbox" class="source-enabled" ${source.enabled ? 'checked' : ''}>
                        <span class="slider round"></span>
                    </label>
                </div>
                <div class="webhook-content">
                    <div class="webhook-input-group mb-3">
                        <label class="form-label">URL RTSP</label>
                        <div class="info-text">${source.url}</div>
                    </div>
                    <div class="webhook-input-group">
                        <label class="form-label">URL Webhook</label>
                        <div class="webhook-input-with-test">
                            <input type="url" class="webhook-input webhook-url" 
                                   value="${source.webhook_url || ''}"
                                   placeholder="https://votre-serveur.com/webhook">
                            <button type="button" class="test-webhook">
                                <span class="icon">🔔</span>
                                Tester
                            </button>
                        </div>
                    </div>
                    <div class="webhook-actions mt-3">
                        <button class="btn btn-sm btn-danger remove-rtsp-btn">
                            <span>🗑️</span> Supprimer
                        </button>
                    </div>
                </div>
            `;
            sourcesList.appendChild(card);
        });
    } catch (error) {
        sourcesList.innerHTML = `
            <div class="list-group-item text-danger">
                Erreur lors du chargement des sources RTSP: ${error.message}
            </div>
        `;
    }
} 