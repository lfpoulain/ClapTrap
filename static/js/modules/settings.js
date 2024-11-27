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
        // Commencer avec les paramètres actuels pour préserver les configs RTSP et VBAN
        const settings = { ...currentSettings };
        
        // Mettre à jour avec les nouveaux paramètres de l'interface
        settings.global = {
            ...(settings.global || {}),
            threshold: document.getElementById('threshold').value,
            delay: document.getElementById('delay').value
        };
        
        settings.microphone = {
            ...(settings.microphone || {}),
            enabled: document.getElementById('webhook-mic-enabled').checked,
            webhook_url: document.getElementById('webhook-mic-url').value,
            audio_source: document.getElementById('micro_source').value.split('|')[1]
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