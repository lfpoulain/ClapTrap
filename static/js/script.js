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
    // ...
    if (typeof window.settings !== 'undefined' && window.settings.saved_vban_sources) {
        // ...
    }
    // ...
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

// ... reste du code ...
