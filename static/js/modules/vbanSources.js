import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';

let vbanSources = [];
let savedVbanSources = [];

export async function initVbanSources() {
    await Promise.all([
        loadVbanSources(),
        loadSavedVbanSources()
    ]);
    renderVbanSources();
}

export async function refreshVbanSources() {
    await loadVbanSources();
    renderVbanSources();
}

async function loadVbanSources() {
    try {
        vbanSources = await callApi('/api/vban/sources', 'GET');
    } catch (error) {
        showError('Erreur lors du chargement des sources VBAN');
    }
}

async function loadSavedVbanSources() {
    try {
        savedVbanSources = await callApi('/api/vban/saved-sources', 'GET');
    } catch (error) {
        showError('Erreur lors du chargement des sources VBAN sauvegardées');
    }
}

function renderVbanSources() {
    // Code de rendu des sources VBAN...
}

// Autres fonctions spécifiques aux sources VBAN... 