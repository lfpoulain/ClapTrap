import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

// Initialiser les paramètres avec une copie profonde des paramètres de la fenêtre
let currentSettings = window.settings ? JSON.parse(JSON.stringify(window.settings)) : {
    global: {
        threshold: "0.5",
        delay: "1.0"
    },
    microphone: {
        enabled: false,
        webhook_url: "",
        audio_source: "default"
    }
};

export function getCurrentSettings() {
    return JSON.parse(JSON.stringify(currentSettings)); // Retourner une copie profonde
}

export function updateSettings(newSettings) {
    try {
        // Fusionner les nouveaux paramètres avec les paramètres existants
        currentSettings = {
            ...currentSettings,
            ...newSettings,
            global: {
                ...currentSettings.global,
                ...(newSettings.global || {})
            },
            microphone: {
                ...currentSettings.microphone,
                ...(newSettings.microphone || {})
            }
        };

        // Sauvegarder dans le sessionStorage pour la persistance
        sessionStorage.setItem('claptrap_settings', JSON.stringify(currentSettings));
    } catch (error) {
        console.error('Erreur lors de la mise à jour des paramètres:', error);
    }
}

export async function saveSettings() {
    try {
        // Récupérer tous les paramètres actuels de l'interface
        const settings = {
            global: {
                threshold: document.getElementById('threshold')?.value || "0.5",
                delay: document.getElementById('delay')?.value || "1.0"
            },
            microphone: {
                enabled: document.getElementById('webhook-mic-enabled')?.checked || false,
                webhook_url: document.getElementById('webhook-mic-url')?.value || "",
                audio_source: document.getElementById('micro_source')?.value?.split('|')[1] || "default"
            }
        };

        // Valider les paramètres avant la sauvegarde
        if (!validateSettings(settings)) {
            showError('Paramètres invalides');
            return false;
        }

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

function validateSettings(settings) {
    try {
        // Valider le seuil
        const threshold = parseFloat(settings.global.threshold);
        if (isNaN(threshold) || threshold < 0 || threshold > 1) {
            return false;
        }

        // Valider le délai
        const delay = parseFloat(settings.global.delay);
        if (isNaN(delay) || delay < 0) {
            return false;
        }

        // Valider l'URL du webhook si activé
        if (settings.microphone.enabled && settings.microphone.webhook_url) {
            try {
                new URL(settings.microphone.webhook_url);
            } catch {
                return false;
            }
        }

        return true;
    } catch (error) {
        console.error('Erreur de validation des paramètres:', error);
        return false;
    }
}

// Charger les paramètres sauvegardés au démarrage
try {
    const savedSettings = sessionStorage.getItem('claptrap_settings');
    if (savedSettings) {
        updateSettings(JSON.parse(savedSettings));
    }
} catch (error) {
    console.error('Erreur lors du chargement des paramètres sauvegardés:', error);
} 