// Fonctions utilitaires
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) {
        console.error('Element notification non trouvé');
        return;
    }
    
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

function showError(message) {
    showNotification(message, 'error');
}

let domReady = false;

// Fonction pour rafraîchir les sources VBAN détectées
function refreshVBANSources() {
    const container = document.getElementById('detectedVBANSources');
    if (!container) {
        console.error('Container detectedVBANSources non trouvé');
        return;
    }

    // Afficher un message de chargement
    container.innerHTML = '<div class="list-group-item text-muted">Chargement des sources VBAN...</div>';

    fetch('/refresh_vban')
        .then(response => response.json())
        .then(data => {
            container.innerHTML = ''; // Nettoyer la liste existante
            
            if (data.sources && data.sources.length > 0) {
                data.sources.forEach(source => {
                    const template = document.getElementById('vbanDetectedSourceTemplate');
                    if (!template) {
                        throw new Error('Template vbanDetectedSourceTemplate non trouvé');
                    }
                    
                    const clone = document.importNode(template.content, true);
                    
                    clone.querySelector('.source-name').textContent = source.name;
                    clone.querySelector('.source-ip').textContent = source.ip;
                    clone.querySelector('.source-port').textContent = source.port;
                    
                    const addButton = clone.querySelector('.add-vban-btn');
                    addButton.addEventListener('click', () => addVBANSource(source));
                    
                    container.appendChild(clone);
                });
            } else {
                container.innerHTML = '<div class="list-group-item text-muted">Aucune source VBAN détectée</div>';
            }
        })
        .catch(error => {
            console.error('Erreur lors du rafraîchissement des sources VBAN:', error);
            container.innerHTML = '<div class="list-group-item text-danger">Erreur lors du chargement des sources VBAN</div>';
            showError('Erreur lors du rafraîchissement des sources VBAN');
        });
}

// Fonction pour afficher les sources VBAN sauvegardées
function displaySavedVBANSources(sources) {
    const container = document.getElementById('savedVBANSources');
    if (!container) {
        console.error('Container savedVBANSources non trouvé');
        return;
    }
    
    container.innerHTML = ''; // Nettoyer la liste existante
    
    // Filtrer pour ne garder que les sources complètement configurées
    const validSources = sources?.filter(source => 
        source.name && 
        source.ip && 
        source.port && 
        source.stream_name
    ) || [];
    
    if (validSources.length > 0) {
        validSources.forEach(source => {
            const template = document.getElementById('vbanSavedSourceTemplate');
            if (!template) {
                console.error('Template vbanSavedSourceTemplate non trouvé');
                return;
            }
            
            const clone = document.importNode(template.content, true);
            
            clone.querySelector('.source-name').textContent = source.name;
            clone.querySelector('.source-ip').textContent = source.ip;
            clone.querySelector('.source-port').textContent = source.port;
            clone.querySelector('.webhook-url').value = source.webhook_url || '';
            clone.querySelector('.source-enabled').checked = source.enabled !== false;
            
            // Gestion du webhook avec validation instantanée
            const webhookInput = clone.querySelector('.webhook-url');
            let typingTimer;
            
            webhookInput.addEventListener('input', (e) => {
                clearTimeout(typingTimer);
                const url = e.target.value.trim();
                
                // Attendre que l'utilisateur arrête de taper pendant 500ms
                typingTimer = setTimeout(() => {
                    if (url === '') {
                        // URL vide est acceptée (suppression du webhook)
                        updateVBANSource(source, { webhook_url: '' });
                    } else if (isValidUrl(url)) {
                        // URL valide
                        webhookInput.classList.remove('invalid');
                        updateVBANSource(source, { webhook_url: url });
                    } else {
                        // URL invalide
                        webhookInput.classList.add('invalid');
                        showError('URL invalide');
                    }
                }, 500);
            });
            
            // Ajouter aussi la validation pour les autres champs webhook
            const enabledSwitch = clone.querySelector('.source-enabled');
            enabledSwitch.addEventListener('change', () => {
                updateVBANSource(source, {
                    enabled: enabledSwitch.checked
                });
            });
            
            const removeButton = clone.querySelector('.remove-vban-btn');
            removeButton.addEventListener('click', () => removeVBANSource(source));
            
            container.appendChild(clone);
        });
    } else {
        container.innerHTML = '<div class="list-group-item text-muted">Aucune source VBAN configurée</div>';
    }
}

// Fonction d'initialisation principale
function initializeApp() {
    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshVBANSources);
    }
    
    // Ajouter le gestionnaire pour le bouton de démarrage
    const startButton = document.getElementById('startButton');
    if (startButton) {
        startButton.addEventListener('click', startDetection);
    }
    
    // Ajouter le gestionnaire pour le bouton d'arrêt
    const stopButton = document.getElementById('stopButton');
    if (stopButton) {
        stopButton.addEventListener('click', stopDetection);
    }
    
    // Vérifier l'existence de settings avant de l'utiliser
    if (typeof window.settings !== 'undefined') {
        // Charger les sources sauvegardées initiales
        displaySavedVBANSources(window.settings.saved_vban_sources || []);
    } else {
        console.error('Settings non définis');
        showNotification('Erreur de chargement des paramètres', 'error');
    }
    
    // Rafraîchir les sources détectées au chargement
    refreshVBANSources();

    // Configuration Socket.IO
    initializeSocketIO();

    // Sauvegarde automatique des paramètres globaux
    const thresholdInput = document.getElementById('threshold');
    const delayInput = document.getElementById('delay');

    if (thresholdInput) {
        thresholdInput.addEventListener('change', () => {
            updateGlobalSettings({
                threshold: thresholdInput.value
            });
        });
    }

    if (delayInput) {
        delayInput.addEventListener('change', () => {
            updateGlobalSettings({
                delay: delayInput.value
            });
        });
    }

    // Sauvegarde automatique des paramètres microphone
    const microphoneSelect = document.getElementById('micro_source');
    const micWebhookInput = document.getElementById('webhook-mic-url');
    const micWebhookEnabled = document.getElementById('webhook-mic-enabled');

    if (microphoneSelect) {
        microphoneSelect.addEventListener('change', () => {
            const [deviceIndex, deviceName] = microphoneSelect.value.split('|');
            updateMicrophoneSettings({
                device_index: deviceIndex,
                audio_source: deviceName
            });
        });
    }

    if (micWebhookInput) {
        let typingTimer;
        
        micWebhookInput.addEventListener('input', (e) => {
            clearTimeout(typingTimer);
            const url = e.target.value.trim();
            
            typingTimer = setTimeout(() => {
                if (url === '') {
                    updateMicrophoneSettings({ webhook_url: '' });
                } else if (isValidUrl(url)) {
                    micWebhookInput.classList.remove('invalid');
                    updateMicrophoneSettings({ webhook_url: url });
                } else {
                    micWebhookInput.classList.add('invalid');
                    showError('URL invalide');
                }
            }, 500);
        });
    }

    if (micWebhookEnabled) {
        micWebhookEnabled.addEventListener('change', () => {
            updateMicrophoneSettings({
                enabled: micWebhookEnabled.checked
            });
        });
    }

    initializeRTSPWebhooks();

    // Trouve le curseur de précision et son affichage
    const thresholdSlider = document.getElementById('threshold');
    const thresholdValue = document.getElementById('threshold-value');

    // Met à jour l'affichage quand le curseur bouge
    thresholdSlider.addEventListener('input', function() {
        thresholdValue.textContent = this.value;
    });

    // Sauvegarde la valeur quand le curseur est relâché
    thresholdSlider.addEventListener('change', function() {
        updateGlobalSettings({
            threshold: this.value
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    domReady = true;
    initializeApp();
});

// Fonction pour initialiser Socket.IO
function initializeSocketIO() {
    const socket = io.connect('http://' + document.domain + ':16045', {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('Connecté au serveur Socket.IO');
        showNotification('Connecté au serveur', 'success');
    });

    socket.on('connect_error', (error) => {
        console.error('Erreur de connexion Socket.IO:', error);
        const startButton = document.getElementById('startButton');
        if (startButton && startButton.style.display !== 'inline-flex') {
            showNotification('Erreur de connexion au serveur', 'error');
        }
    });

    // Gestion des claps
    socket.on('clap', (data) => {
        console.log('Clap détecté:', data);
        
        // Gestion du detection_display
        const display = document.getElementById('detection_display');
        if (display) {
            display.innerHTML = '👏';
            display.classList.add('clap');
            
            // Nettoyer après l'animation
            setTimeout(() => {
                display.innerHTML = '';
                display.classList.remove('clap');
            }, 1000);
        }

        // Gestion de l'icône clap
        const clapIcon = document.querySelector('.clap-icon');
        if (clapIcon) {
            clapIcon.classList.add('active');
            setTimeout(() => {
                clapIcon.classList.remove('active');
            }, 1000);
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
}

// Modifier les références à settings dans le reste du code
function updateVBANSource(source, updates) {
    const updatedSource = { ...source, ...updates };
    
    fetch('/api/vban/update', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedSource)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Erreur lors de la mise à jour de la source');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification('Source VBAN mise à jour avec succès', 'success');
            
            // Mettre à jour les settings locaux
            if (typeof window.settings !== 'undefined' && window.settings.saved_vban_sources) {
                const index = window.settings.saved_vban_sources.findIndex(s => 
                    s.ip === source.ip && s.stream_name === source.stream_name
                );
                if (index !== -1) {
                    window.settings.saved_vban_sources[index] = updatedSource;
                }
            }
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError(error.message);
        // Recharger l'affichage pour revenir à l'état précédent
        displaySavedVBANSources(window.settings.saved_vban_sources || []);
    });
}

function addVBANSource(source) {
    // ...
    if (typeof window.settings === 'undefined') {
        window.settings = {};
    }
    if (!Array.isArray(window.settings.saved_vban_sources)) {
        window.settings.saved_vban_sources = [];
    }
    // ...
}

// Fonction pour démarrer la détection
async function startDetection() {
    try {
        const selectedMicro = document.getElementById('micro_source')?.value;
        if (!selectedMicro) {
            throw new Error('Aucun microphone sélectionné');
        }

        const [deviceIndex, deviceName] = selectedMicro.split('|');

        // Récupérer tous les paramètres actuels
        const settings = {
            global: {
                threshold: document.getElementById('threshold')?.value || '0.5',
                delay: document.getElementById('delay')?.value || '1.0',
                chunk_duration: 0.5,
                buffer_duration: 1.0
            },
            microphone: {
                device_index: deviceIndex,
                audio_source: deviceName,
                webhook_url: document.getElementById('webhook-mic-url')?.value || '',
                enabled: document.getElementById('webhook-mic-enabled')?.checked || false
            },
            rtsp_sources: [],
            vban: window.settings?.vban || {
                stream_name: "",
                ip: "0.0.0.0",
                port: 6980,
                webhook_url: "",
                enabled: false
            }
        };

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
        const startBtn = document.getElementById('startButton');
        const stopBtn = document.getElementById('stopButton');
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'block';
        
        showNotification('Détection démarrée avec succès', 'success');

    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Erreur:', error);
    }
}

// Fonction pour arrêter la détection
async function stopDetection() {
    try {
        const response = await fetch('/stop_detection', {
            method: 'POST'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erreur lors de l\'arrêt de la détection');
        }

        // Mettre à jour l'interface
        const startBtn = document.getElementById('startButton');
        const stopBtn = document.getElementById('stopButton');
        if (startBtn) startBtn.style.display = 'block';
        if (stopBtn) stopBtn.style.display = 'none';
        
        showNotification('Détection arrêtée', 'success');

    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Erreur:', error);
    }
}

// Fonction pour mettre à jour les paramètres globaux
function updateGlobalSettings(updates) {
    if (typeof window.settings === 'undefined') {
        window.settings = { global: {} };
    }

    const updatedSettings = {
        ...window.settings,
        global: {
            ...window.settings.global,
            ...updates
        }
    };

    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedSettings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.settings = updatedSettings;
            showNotification('Paramètres sauvegardés', 'success');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError('Erreur lors de la sauvegarde des paramètres');
    });
}

// Fonction pour mettre à jour les paramètres du microphone
function updateMicrophoneSettings(updates) {
    if (typeof window.settings === 'undefined') {
        window.settings = { microphone: {} };
    }

    const updatedSettings = {
        ...window.settings,
        microphone: {
            ...window.settings.microphone,
            ...updates
        }
    };

    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedSettings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.settings = updatedSettings;
            showNotification('Paramètres microphone sauvegardés', 'success');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError('Erreur lors de la sauvegarde des paramètres microphone');
    });
}

function initializeRTSPWebhooks() {
    document.querySelectorAll('[id^="webhook-rtsp-"]').forEach(input => {
        if (input.type === 'url') {
            let typingTimer;
            
            input.addEventListener('input', (e) => {
                clearTimeout(typingTimer);
                const url = e.target.value.trim();
                const index = input.id.split('-')[2];
                
                typingTimer = setTimeout(() => {
                    if (url === '') {
                        updateRTSPSettings(index - 1, { webhook_url: '' });
                    } else if (isValidUrl(url)) {
                        input.classList.remove('invalid');
                        updateRTSPSettings(index - 1, { webhook_url: url });
                    } else {
                        input.classList.add('invalid');
                        showError('URL invalide');
                    }
                }, 500);
            });
        } else if (input.type === 'checkbox') {
            input.addEventListener('change', () => {
                const index = input.id.split('-')[2];
                updateRTSPSettings(index - 1, {
                    enabled: input.checked
                });
            });
        }
    });
}

function updateRTSPSettings(index, updates) {
    if (typeof window.settings === 'undefined') {
        window.settings = { rtsp_sources: [] };
    }

    if (!window.settings.rtsp_sources[index]) {
        window.settings.rtsp_sources[index] = {};
    }

    const updatedSettings = {
        ...window.settings,
        rtsp_sources: window.settings.rtsp_sources.map((source, i) => 
            i === index ? { ...source, ...updates } : source
        )
    };

    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedSettings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.settings = updatedSettings;
            showNotification('Paramètres RTSP sauvegardés', 'success');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError('Erreur lors de la sauvegarde des paramètres RTSP');
    });
}

// Fonction pour valider une URL
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// ... reste du code ...

