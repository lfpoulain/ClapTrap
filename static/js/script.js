import { initAudioSources, updateAudioSources } from './modules/audioSources.js';
import { initVbanSources, refreshVbanSources } from './modules/vbanSources.js';
import { initRtspSources } from './modules/rtspSources.js';
import { initWebhooks } from './modules/webhooks.js';
import { setupEventListeners } from './modules/events.js';
import { updateSettings } from './modules/settings.js';
import { initializeSocketIO } from './modules/socket.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialiser Socket.IO
    initializeSocketIO();
    
    // Initialiser les paramètres avec les valeurs du serveur
    if (window.settings) {
        updateSettings(window.settings);
    }
    
    initAudioSources();
    initVbanSources();
    initRtspSources();
    initWebhooks();
    setupEventListeners();
});

