import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

let currentSettings = window.settings || {};

export function getCurrentSettings() {
    return currentSettings;
}

export function updateSettings(newSettings) {
    currentSettings = { ...currentSettings, ...newSettings };
}

export async function saveSettings() {
    try {
        // Récupérer tous les paramètres actuels de l'interface
        const audioSourceValue = document.getElementById('micro_source').value;
        const [deviceId, deviceName] = audioSourceValue.split('|');

        const settings = {
            global: {
                threshold: document.getElementById('threshold').value,
                delay: document.getElementById('delay').value
            },
            microphone: {
                enabled: document.getElementById('webhook-mic-enabled').checked,
                webhook_url: document.getElementById('webhook-mic-url').value,
                audio_source: deviceName,
                device_id: deviceId
            }
        };

        const response = await callApi('/api/settings/save', 'POST', settings);
        if (response.success) {
            updateSettings(settings);
            showSuccess('Paramètres sauvegardés');
            return true;
        }
        return false;
    } catch (error) {
        showError('Erreur lors de la sauvegarde des paramètres');
        return false;
    }
} 