import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { validateSettings, compareWithDOMValues, validateDOM } from './settingsValidator.js';

let currentSettings = {};

export function getCurrentSettings() {
    return currentSettings;
}

export function updateSettings(newSettings) {
    currentSettings = { ...currentSettings, ...newSettings };
}

// Synchronise les valeurs de l'interface avec currentSettings
function syncWithDOM() {
    // Récupérer les éléments de l'interface
    const threshold = document.getElementById('threshold');
    const delay = document.getElementById('delay');
    const micEnabled = document.getElementById('webhook-mic-enabled');
    const micUrl = document.getElementById('webhook-mic-url');
    const micSource = document.getElementById('micro_source');

    const [deviceId, deviceName] = micSource ? micSource.value.split('|') : ['0', 'default'];

    // Synchroniser les paramètres globaux et du microphone
    const updatedSettings = {
        ...currentSettings,
        global: {
            ...currentSettings.global,
            threshold: threshold ? threshold.value : currentSettings.global.threshold,
            delay: delay ? delay.value : currentSettings.global.delay
        },
        microphone: {
            ...currentSettings.microphone,
            enabled: micEnabled ? micEnabled.checked : false,
            webhook_url: micUrl ? micUrl.value : '',
            audio_source: deviceName || 'default',
            device_index: deviceId || '0'
        }
    };

    // Synchroniser les sources VBAN
    const savedVbanContainer = document.getElementById('savedVBANSources');
    if (savedVbanContainer) {
        const savedVbanSources = Array.from(savedVbanContainer.querySelectorAll('.list-group-item:not(.text-muted)')).map(element => {
            const name = element.querySelector('.source-name')?.textContent;
            const ip = element.querySelector('.source-ip')?.textContent;
            const port = parseInt(element.querySelector('.source-port')?.textContent || '6980');
            const webhookUrl = element.querySelector('.webhook-url')?.value || '';
            const enabled = element.querySelector('.source-enabled')?.checked || false;

            // Ne pas inclure les sources qui n'ont pas de nom (messages d'erreur ou placeholders)
            if (!name) return null;

            return {
                name,
                ip,
                port,
                stream_name: name,
                webhook_url: webhookUrl,
                enabled
            };
        }).filter(source => source !== null); // Filtrer les sources nulles

        console.log('📝 Sources VBAN synchronisées:', savedVbanSources);
        updatedSettings.saved_vban_sources = savedVbanSources;
    }

    // Synchroniser les sources RTSP
    const rtspContainer = document.getElementById('rtspStreamsContainer');
    if (rtspContainer) {
        const rtspSources = Array.from(rtspContainer.querySelectorAll('.webhook-card')).map(element => {
            const id = element.querySelector('.stream-enabled')?.dataset.id;
            const name = element.querySelector('h4')?.textContent.trim().replace('📹', '').trim();
            const url = element.querySelector('.rtsp-url')?.value || '';
            const webhookUrl = element.querySelector('.webhook-url')?.value || '';
            const enabled = element.querySelector('.stream-enabled')?.checked || false;

            return {
                id,
                name,
                url,
                webhook_url: webhookUrl,
                enabled
            };
        });

        updatedSettings.rtsp_sources = rtspSources;
    }

    // Mettre à jour currentSettings
    currentSettings = updatedSettings;

    console.log('📝 Paramètres synchronisés:', currentSettings);
    return currentSettings;
}

export function initSettings(initialSettings) {
    console.log(' Initialisation des paramètres...');
    
    // Valider la structure du DOM
    const domValidation = validateDOM();
    if (!domValidation.isValid) {
        console.error(' Éléments manquants dans le DOM:', domValidation.missingElements);
        showError('Erreur: Certains éléments de l\'interface sont manquants');
        return false;
    }

    // Valider et compléter les paramètres
    const { settings, errors, isValid } = validateSettings(initialSettings);
    if (!isValid) {
        console.warn(' Problèmes détectés dans les paramètres:', errors);
        showError('Les paramètres ont été corrigés. Veuillez vérifier les valeurs.');
    }

    // Mettre à jour les paramètres validés
    currentSettings = settings;
    
    // Vérifier la cohérence avec l'interface
    const { hasDifferences, differences } = compareWithDOMValues(settings);
    if (hasDifferences) {
        console.warn(' Différences détectées entre les paramètres et l\'interface:', differences);
        showError('Incohérence détectée entre les paramètres et l\'interface');
    }

    console.log(' Paramètres initialisés:', currentSettings);
    return true;
}

export async function saveSettings() {
    try {
        // Synchroniser avec les valeurs de l'interface
        const updatedSettings = syncWithDOM();
        console.log(' Paramètres synchronisés avec l\'interface:', updatedSettings);

        // Valider les paramètres avant la sauvegarde
        const { settings, errors, isValid } = validateSettings(updatedSettings);
        if (!isValid) {
            console.warn(' Problèmes détectés avant la sauvegarde:', errors);
            showError('Certains paramètres sont invalides ou manquants');
            return false;
        }

        // Sauvegarder les paramètres validés
        const response = await callApi('/api/settings/save', 'POST', settings);
        if (response.success) {
            currentSettings = settings;
            showSuccess('Paramètres sauvegardés');
            return true;
        }
        return false;
    } catch (error) {
        showError('Erreur lors de la sauvegarde des paramètres');
        return false;
    }
}