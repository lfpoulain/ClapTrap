import { initAudioSources } from './modules/audioSources.js';
import { initVbanSources, refreshVbanSources } from './modules/vbanSources.js';
import { initRtspSources } from './modules/rtspSources.js';
import { initWebhooks } from './modules/webhooks.js';
import { setupEventListeners } from './modules/events.js';
import { updateSettings } from './modules/settings.js';
import { initializeSocketIO } from './modules/socketHandlers.js';

document.addEventListener('DOMContentLoaded', () => {
    if (window.settings) {
        updateSettings(window.settings);
    }
    
    initAudioSources();
    initVbanSources();
    initRtspSources();
    initWebhooks();
    setupEventListeners();
    
    // Initialiser Socket.IO
    const socket = initializeSocketIO();
});

