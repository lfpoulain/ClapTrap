import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { validateWebhookUrl } from './utils.js';

export function initWebhooks() {
    setupMicrophoneWebhook();
    // Initialiser les boutons de test immédiatement et configurer un observateur pour les nouveaux boutons
    setupTestWebhookButtons();
    setupWebhookButtonsObserver();
}

function setupMicrophoneWebhook() {
    const enabledCheckbox = document.getElementById('webhook-mic-enabled');
    const webhookInput = document.getElementById('webhook-mic-url');
    
    if (enabledCheckbox && webhookInput) {
        enabledCheckbox.addEventListener('change', function() {
            webhookInput.closest('.webhook-content').style.display = 
                this.checked ? 'block' : 'none';
        });
    }
}

function setupWebhookButtonsObserver() {
    // Observer pour détecter les nouveaux boutons de test ajoutés dynamiquement
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        const newButtons = node.querySelectorAll('.test-webhook:not([data-initialized])');
                        newButtons.forEach(setupTestWebhookButton);
                    }
                });
            }
        });
    });

    // Observer le conteneur des sources RTSP
    const rtspContainer = document.getElementById('rtspStreamsContainer');
    if (rtspContainer) {
        observer.observe(rtspContainer, { childList: true, subtree: true });
    }

    // Observer le conteneur des sources VBAN
    const vbanContainer = document.getElementById('savedVBANSources');
    if (vbanContainer) {
        observer.observe(vbanContainer, { childList: true, subtree: true });
    }
}

function setupTestWebhookButtons() {
    document.querySelectorAll('.test-webhook:not([data-initialized])').forEach(setupTestWebhookButton);
}

function setupTestWebhookButton(button) {
    // Marquer le bouton comme initialisé
    button.setAttribute('data-initialized', 'true');
    
    button.addEventListener('click', async function() {
        const source = this.dataset.source;
        let webhookInput;
        
        // Déterminer l'input webhook en fonction de la source
        if (source === 'mic') {
            webhookInput = document.getElementById('webhook-mic-url');
        } else if (source.startsWith('vban-')) {
            webhookInput = this.closest('.webhook-input-with-test')?.querySelector('.webhook-url');
        } else if (source.startsWith('rtsp-')) {
            webhookInput = this.closest('.webhook-input-with-test')?.querySelector('.webhook-url');
        }
        
        if (!webhookInput || !webhookInput.value) {
            showError('URL du webhook non définie');
            return;
        }

        if (!validateWebhookUrl(webhookInput.value)) {
            showError('URL du webhook invalide');
            return;
        }

        // Sauvegarder le contenu original du bouton
        const buttonContent = this.innerHTML;
        
        try {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Test...';
            
            await testWebhook(source, webhookInput.value);
            showSuccess('Test du webhook réussi');
        } catch (error) {
            showError('Échec du test du webhook: ' + error.message);
        } finally {
            this.disabled = false;
            this.innerHTML = buttonContent;
        }
    });
}

async function testWebhook(source, url) {
    try {
        const response = await callApi('/api/webhook/test', 'POST', {
            source,
            url
        });
        
        if (!response.success) {
            throw new Error(response.error || 'Échec du test');
        }
        
        return response;
    } catch (error) {
        console.error('Erreur lors du test du webhook:', error);
        throw error;
    }
}