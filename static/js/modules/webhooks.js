import { callApi } from './api.js';
import { showError, showSuccess } from './utils.js';
import { validateWebhookUrl } from './utils.js';

export function initWebhooks() {
    setupMicrophoneWebhook();
    setupTestWebhookButtons();
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

function setupTestWebhookButtons() {
    document.querySelectorAll('.test-webhook').forEach(button => {
        button.addEventListener('click', async function() {
            const source = this.dataset.source;
            const webhookInput = document.getElementById(`webhook-${source}-url`);
            
            if (!webhookInput || !webhookInput.value) {
                showError('URL du webhook non définie');
                return;
            }

            if (!validateWebhookUrl(webhookInput.value)) {
                showError('URL du webhook invalide');
                return;
            }

            try {
                await testWebhook(source, webhookInput.value);
                showSuccess('Test du webhook réussi');
            } catch (error) {
                showError('Échec du test du webhook');
            }
        });
    });
}

async function testWebhook(source, url) {
    return await callApi('/api/webhook/test', 'POST', {
        source,
        url
    });
} 