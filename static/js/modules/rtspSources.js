import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

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
        const enabledCheckbox = document.getElementById(`webhook-rtsp-${index + 1}-enabled`);
        const webhookInput = document.getElementById(`webhook-rtsp-${index + 1}-url`);
        
        if (enabledCheckbox && webhookInput) {
            enabledCheckbox.addEventListener('change', function() {
                webhookInput.closest('.webhook-content').style.display = 
                    this.checked ? 'block' : 'none';
            });
        }
    });
}

export async function updateRtspWebhook(streamId, webhookUrl) {
    try {
        await callApi('/api/rtsp/webhook', 'POST', {
            streamId,
            webhookUrl
        });
        showSuccess('Webhook RTSP mis à jour');
    } catch (error) {
        showError('Erreur lors de la mise à jour du webhook RTSP');
    }
} 