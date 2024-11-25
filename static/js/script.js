// Fonction pour exécuter les tests (déplacée en dehors du DOMContentLoaded)
async function runTests() {
    try {
        const response = await fetch('/run_tests', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Tests exécutés avec succès', 'success');
            console.log('Résultats des tests:', data);
        } else {
            showNotification(data.error || 'Erreur lors de l\'exécution des tests', 'error');
        }
    } catch (error) {
        showNotification('Erreur lors de l\'exécution des tests', 'error');
        console.error('Erreur:', error);
    }
}

// Fonction pour afficher les notifications (déplacée en dehors du DOMContentLoaded)
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    // Force le reflow pour déclencher l'animation
    notification.offsetHeight;
    
    // Ajoute la classe show pour déclencher l'animation
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
        // Attendre la fin de l'animation avant de cacher
        setTimeout(() => {
            notification.style.display = 'none';
        }, 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    // Éléments de l'interface
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const audioSource = document.getElementById('audio_source');
    const threshold = document.getElementById('threshold');
    const delay = document.getElementById('delay');
    const refreshVbanButton = document.getElementById('refresh_vban');
    const thresholdOutput = threshold.nextElementSibling;

    // Gestion des webhooks
    const webhookToggles = document.querySelectorAll('[id^="webhook-"][id$="-enabled"]');
    const webhookInputs = document.querySelectorAll('.webhook-input');
    const testWebhookButtons = document.querySelectorAll('.test-webhook');

    // Mise à jour de l'affichage du seuil
    threshold.addEventListener('input', function() {
        thresholdOutput.textContent = this.value;
    });

    // Gestion des toggles webhook
    webhookToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const content = this.closest('.webhook-card').querySelector('.webhook-content');
            content.style.display = this.checked ? 'block' : 'none';
        });
    });

    // Fonction pour collecter les paramètres
    function getSettings() {
        const settings = {
            audio_source: audioSource.value,
            threshold: parseFloat(threshold.value),
            delay: parseFloat(delay.value),
            webhooks: {}
        };

        // Collecter les webhooks activés
        webhookToggles.forEach(toggle => {
            const id = toggle.id.replace('-enabled', '');
            const url = document.getElementById(id + '-url')?.value;
            if (toggle.checked && url) {
                settings.webhooks[id] = url;
            }
        });

        return settings;
    }

    // Démarrer la détection
    startButton.addEventListener('click', async function() {
        try {
            const settings = getSettings();
            const response = await fetch('/start_detection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (response.ok) {
                showNotification('Détection démarrée avec succès');
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-flex';
            } else {
                showNotification(data.error || 'Erreur lors du démarrage de la détection', 'error');
            }
        } catch (error) {
            showNotification('Erreur de connexion au serveur', 'error');
            console.error('Erreur:', error);
        }
    });

    // Arrêter la détection
    stopButton.addEventListener('click', async function() {
        try {
            const response = await fetch('/stop_detection', {
                method: 'POST'
            });

            const data = await response.json();
            
            if (response.ok) {
                showNotification('Détection arrêtée');
                stopButton.style.display = 'none';
                startButton.style.display = 'inline-flex';
                
                // Nettoyer la liste des sons détectés
                const labelsDiv = document.getElementById('detected_labels');
                labelsDiv.innerHTML = '';
                
                // Nettoyer aussi l'affichage du clap si présent
                const display = document.getElementById('detection_display');
                display.innerHTML = '';
                display.classList.remove('clap');
            } else {
                showNotification(data.error || 'Erreur lors de l\'arrêt de la détection', 'error');
            }
        } catch (error) {
            showNotification('Erreur de connexion au serveur', 'error');
            console.error('Erreur:', error);
        }
    });

    // Rafraîchir les sources VBAN
    refreshVbanButton.addEventListener('click', async function() {
        try {
            refreshVbanButton.classList.add('refreshing');
            const response = await fetch('/refresh_vban');
            const data = await response.json();
            
            if (response.ok) {
                // Mettre à jour la liste des sources
                const currentSource = audioSource.value;
                audioSource.innerHTML = ''; // Vider la liste actuelle
                
                // Recréer les options avec les nouvelles sources
                data.sources.forEach(source => {
                    const option = document.createElement('option');
                    option.value = source.url || source.name;
                    option.textContent = source.name;
                    option.selected = source.url === currentSource || source.name === currentSource;
                    audioSource.appendChild(option);
                });
                
                showNotification('Sources VBAN mises à jour');
            } else {
                showNotification(data.error || 'Erreur lors de la mise à jour des sources VBAN', 'error');
            }
        } catch (error) {
            showNotification('Erreur de connexion au serveur', 'error');
            console.error('Erreur:', error);
        } finally {
            refreshVbanButton.classList.remove('refreshing');
        }
    });

    // Tester les webhooks
    testWebhookButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const source = this.dataset.source;
            const urlInput = this.closest('.webhook-card').querySelector('.webhook-input');
            const url = urlInput.value;

            if (!url) {
                showNotification('Veuillez entrer une URL de webhook', 'warning');
                return;
            }

            try {
                const response = await fetch('/test_webhook', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: url,
                        source: source
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    showNotification('Test du webhook réussi');
                } else {
                    showNotification(data.error || 'Échec du test du webhook', 'error');
                }
            } catch (error) {
                showNotification('Erreur lors du test du webhook', 'error');
                console.error('Erreur:', error);
            }
        });
    });

    // Configuration Socket.IO
    const socket = io.connect('http://' + document.domain + ':' + 16045);

    socket.on('connect', () => {
        console.log('Connecté au serveur Socket.IO');
    });

    socket.on('connect_error', (error) => {
        console.error('Erreur de connexion Socket.IO:', error);
        showNotification('Erreur de connexion au serveur', 'error');
    });

    socket.on('clap', (data) => {
        console.log('Clap détecté:', data);
        const display = document.getElementById('detection_display');
        display.innerHTML = '👏';
        display.classList.add('clap');
        
        setTimeout(() => {
            display.innerHTML = '';
            display.classList.remove('clap');
        }, 500);
    });

    socket.on('labels', (data) => {
        console.log('Labels reçus:', data);
        const labelsDiv = document.getElementById('detected_labels');
        labelsDiv.innerHTML = '';
        
        if (data.detected && Array.isArray(data.detected)) {
            data.detected.forEach(item => {
                const labelElement = document.createElement('p');
                labelElement.textContent = item.label;
                labelsDiv.appendChild(labelElement);
            });
        }
    });

    // Vérifier l'état initial de la détection
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            if (data.running) {
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-flex';
            } else {
                startButton.style.display = 'inline-flex';
                stopButton.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Erreur lors de la vérification du statut:', error);
        });
});
