import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { saveSettings } from './settings.js';

let audioSources = [];

export async function initAudioSources() {
    try {
        const sources = await callApi('/api/audio-sources', 'GET');
        audioSources = sources.filter(source => source.type === 'microphone');
        setupMicrophoneWebhook();
    } catch (error) {
        showError('Erreur lors du chargement des sources audio');
    }
}

function setupMicrophoneWebhook() {
    const webhookInput = document.getElementById('webhook-mic-url');
    const enabledSwitch = document.getElementById('webhook-mic-enabled');
    
    if (webhookInput) {
        // Ajouter un délai de 500ms après la dernière frappe avant de sauvegarder
        let timeout;
        webhookInput.addEventListener('input', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(async () => {
                const newWebhookUrl = e.target.value.trim();
                await updateMicrophoneWebhook(newWebhookUrl);
            }, 500);
        });
    }

    if (enabledSwitch) {
        enabledSwitch.addEventListener('change', async (e) => {
            const enabled = e.target.checked;
            await updateMicrophoneEnabled(enabled);
        });
    }
}

async function updateMicrophoneWebhook(webhookUrl) {
    try {
        const response = await callApi('/api/microphone/webhook', 'PUT', {
            webhook_url: webhookUrl
        });
        if (response.success) {
            // Sauvegarder les paramètres après la mise à jour réussie
            await saveSettings();
            showSuccess('Webhook du microphone mis à jour');
        } else {
            throw new Error(response.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        showError('Erreur lors de la mise à jour du webhook du microphone');
    }
}

async function updateMicrophoneEnabled(enabled) {
    try {
        const response = await callApi('/api/microphone/enabled', 'PUT', {
            enabled: enabled
        });
        if (response.success) {
            // Sauvegarder les paramètres après la mise à jour réussie
            await saveSettings();
            showSuccess(enabled ? 'Microphone activé' : 'Microphone désactivé');
        } else {
            throw new Error(response.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        showError('Erreur lors de la mise à jour du statut du microphone');
    }
}

function renderAudioSources() {
    const container = document.getElementById('audioSourcesContainer');
    // Code de rendu des sources audio...
}

// Autres fonctions spécifiques aux sources audio... 