// Ajouter cette fonction au début du fichier, avant le DOMContentLoaded
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

// Ajouter au début du fichier
let clapTimeout = null;

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
        const selectedMicro = document.getElementById('micro_source').value;
        const [deviceIndex, deviceName] = selectedMicro.split('|');

        // Récupérer tous les paramètres actuels
        const settings = {
            global: {
                threshold: document.getElementById('threshold').value,
                delay: document.getElementById('delay').value,
                chunk_duration: 0.5,
                buffer_duration: 1.0
            },
            microphone: {
                device_index: deviceIndex,
                audio_source: deviceName,
                webhook_url: document.getElementById('webhook-mic-url').value,
                enabled: document.getElementById('webhook-mic-enabled').checked
            },
            rtsp_sources: [],
            vban: {
                stream_name: "",
                ip: "0.0.0.0",
                port: 6980,
                webhook_url: "",
                enabled: false
            }
        };

        try {
            // Sauvegarder les paramètres avant de démarrer la détection
            const saveResponse = await fetch('/save_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!saveResponse.ok) {
                const errorData = await saveResponse.json();
                throw new Error(errorData.error || 'Erreur lors de la sauvegarde des paramètres');
            }

            // Si la sauvegarde réussit, démarrer la détection
            const startResponse = await fetch('/start_detection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!startResponse.ok) {
                const errorData = await startResponse.json();
                throw new Error(errorData.error || 'Erreur lors du démarrage de la détection');
            }

            // Mettre à jour l'interface
            this.style.display = 'none';
            document.getElementById('stopButton').style.display = 'block';
            showNotification('Détection démarrée avec succès', 'success');

        } catch (error) {
            showNotification(error.message, 'error');
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

    // Configuration Socket.IO avec le port explicite
    const socket = io.connect('http://' + document.domain + ':16045', {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('Connecté au serveur Socket.IO');
        showNotification('Connecté au serveur', 'success');
    });

    socket.on('connect_error', (error) => {
        console.error('Erreur de connexion Socket.IO:', error);
        showNotification('Erreur de connexion au serveur', 'error');
    });

    // Gestion des claps
    socket.on('clap', (data) => {
        console.log('Clap détecté:', data);
        const display = document.getElementById('detection_display');
        if (display) {
            // Afficher directement l'emoji dans la div
            display.innerHTML = '👏';
            display.classList.add('clap');
            
            // Retirer l'emoji et la classe après 500ms
            setTimeout(() => {
                display.innerHTML = '';
                display.classList.remove('clap');
            }, 500);
        } else {
            console.error('Element detection_display non trouvé');
        }
    });

    // Gestion des labels
    socket.on('labels', (data) => {
        console.log('Labels reçus:', data);
        const labelsDiv = document.getElementById('detected_labels');
        if (!labelsDiv) {
            console.error('Element detected_labels non trouvé');
            return;
        }

        // S'assurer que le conteneur est visible
        labelsDiv.style.display = 'block';
        
        // Vérifier si data.detected existe et est un tableau
        if (data.detected && Array.isArray(data.detected)) {
            // Vider le conteneur des labels précédents
            labelsDiv.innerHTML = '';
            
            // Trier les labels par score et prendre les 5 premiers
            const sortedLabels = [...data.detected]
                .sort((a, b) => b.score - a.score)
                .slice(0, 5);
            
            // Créer un élément pour chaque label
            sortedLabels.forEach(item => {
                const labelElement = document.createElement('div');
                labelElement.classList.add('label');
                labelElement.textContent = `${item.label} (${Math.round(item.score * 100)}%)`;
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

    // Ajouter un écouteur pour sauvegarder la sélection du micro quand elle change
    document.getElementById('micro_source').addEventListener('change', async function() {
        const [deviceIndex, deviceName] = this.value.split('|');
        const settings = {
            microphone: {
                device_index: deviceIndex,
                audio_source: deviceName
            }
        };
        
        try {
            const response = await fetch('/save_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la sauvegarde de la source audio');
            }
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de la source audio:', error);
        }
    });

    // Modifier la fonction qui gère les événements WebSocket
    socket.on('message', function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'clap_detected') {
            // Afficher l'icône
            const clapIcon = document.querySelector('.clap-icon');
            clapIcon.classList.add('active');
            
            // Nettoyer le timeout précédent si existant
            if (clapTimeout) {
                clearTimeout(clapTimeout);
            }
            
            // Masquer l'icône après 500ms
            clapTimeout = setTimeout(() => {
                clapIcon.classList.remove('active');
            }, 500);
        }
    });
});
