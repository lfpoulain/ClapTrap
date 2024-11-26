import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

let audioSources = [];

export async function initAudioSources() {
    try {
        const sources = await callApi('/api/audio-sources', 'GET');
        audioSources = sources.filter(source => source.type === 'microphone');
        renderAudioSources();
    } catch (error) {
        showError('Erreur lors du chargement des sources audio');
    }
}

export async function updateAudioSources() {
    try {
        const sources = await callApi('/api/audio-sources', 'GET');
        audioSources = sources.filter(source => source.type === 'microphone');
        renderAudioSources();
    } catch (error) {
        showError('Erreur lors de la mise à jour des sources audio');
    }
}

function renderAudioSources() {
    const container = document.getElementById('audioSourcesContainer');
    // Code de rendu des sources audio...
}

// Autres fonctions spécifiques aux sources audio... 