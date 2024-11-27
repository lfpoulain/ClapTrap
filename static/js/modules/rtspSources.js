import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { saveSettings } from './settings.js';

let rtspStreams = [];

export async function initRtspSources() {
    try {
        rtspStreams = await callApi('/api/rtsp/streams', 'GET');
        setupRtspWebhooks();
    } catch (error) {
        showError('Erreur lors du chargement des flux RTSP');
    }
}

function setupRtspWebhooks() {
    rtspStreams.forEach((stream, index) => {
        const webhookInput = document.getElementById(`webhook-rtsp-${index + 1}-url`);
        const enabledSwitch = document.getElementById(`webhook-rtsp-${index + 1}-enabled`);
        
        if (webhookInput) {
            // Ajouter un délai de 500ms après la dernière frappe avant de sauvegarder
            let timeout;
            webhookInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(async () => {
                    const newWebhookUrl = e.target.value.trim();
                    await updateRtspWebhook(stream.id, newWebhookUrl);
                }, 500);
            });
        }

        if (enabledSwitch) {
            enabledSwitch.addEventListener('change', async (e) => {
                const enabled = e.target.checked;
                await updateRtspEnabled(stream.id, enabled);
            });
        }
    });
}

async function updateRtspWebhook(streamId, webhookUrl) {
    try {
        const response = await callApi('/api/rtsp/webhook', 'PUT', {
            stream_id: streamId,
            webhook_url: webhookUrl
        });
        if (response.success) {
            // Sauvegarder les paramètres après la mise à jour réussie
            await saveSettings();
            showSuccess('Webhook RTSP mis à jour');
        } else {
            throw new Error(response.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        showError('Erreur lors de la mise à jour du webhook RTSP');
    }
}

async function updateRtspEnabled(streamId, enabled) {
    try {
        const response = await callApi('/api/rtsp/enabled', 'PUT', {
            stream_id: streamId,
            enabled: enabled
        });
        if (response.success) {
            // Sauvegarder les paramètres après la mise à jour réussie
            await saveSettings();
            showSuccess(enabled ? 'Flux RTSP activé' : 'Flux RTSP désactivé');
        } else {
            throw new Error(response.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        showError('Erreur lors de la mise à jour du statut du flux RTSP');
    }
} 