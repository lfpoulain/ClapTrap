// Ajouter au début du fichier
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

function showError(message) {
    showNotification(message, 'error');
}

// Fonction pour afficher les sources VBAN sauvegardées
function displaySavedVBANSources(sources) {
    const container = document.getElementById('savedVBANSources');
    if (!container) {
        console.error('Container savedVBANSources non trouvé');
        return;
    }
    
    container.innerHTML = ''; // Nettoyer la liste existante
    
    if (sources && sources.length > 0) {
        sources.forEach(source => {
            const template = document.getElementById('vbanSavedSourceTemplate');
            if (!template) {
                console.error('Template vbanSavedSourceTemplate non trouvé');
                return;
            }
            
            const clone = document.importNode(template.content, true);
            
            clone.querySelector('.source-name').textContent = source.name;
            clone.querySelector('.webhook-url').value = source.webhook_url;
            clone.querySelector('.source-enabled').checked = source.enabled;
            
            const removeButton = clone.querySelector('.remove-vban-btn');
            removeButton.addEventListener('click', () => removeVBANSource(source));
            
            container.appendChild(clone);
        });
    } else {
        container.innerHTML = '<div class="list-group-item text-muted">Aucune source VBAN configurée</div>';
    }
}

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

// Fonction pour ajouter une source VBAN
function addVBANSource(source) {
    const newSource = {
        name: source.name,
        ip: source.ip,
        port: source.port,
        stream_name: source.stream_name,
        webhook_url: '',
        enabled: true
    };

    fetch('/api/vban/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(newSource)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Source VBAN ajoutée avec succès');
            // Rafraîchir l'affichage des sources sauvegardées
            if (typeof settings !== 'undefined') {
                settings.saved_vban_sources = settings.saved_vban_sources || [];
                settings.saved_vban_sources.push(newSource);
                displaySavedVBANSources(settings.saved_vban_sources);
            }
        } else {
            throw new Error(data.error || 'Erreur lors de l\'ajout de la source');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError(error.message);
    });
}

// Fonction pour supprimer une source VBAN
function removeVBANSource(source) {
    fetch(`/api/vban/remove`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ip: source.ip,
            stream_name: source.stream_name
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Source VBAN supprimée avec succès');
            // Mettre à jour la liste locale
            if (typeof settings !== 'undefined') {
                settings.saved_vban_sources = settings.saved_vban_sources.filter(s => 
                    !(s.ip === source.ip && s.stream_name === source.stream_name)
                );
                displaySavedVBANSources(settings.saved_vban_sources);
            }
        } else {
            throw new Error(data.error || 'Erreur lors de la suppression de la source');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showError(error.message);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const refreshBtn = document.getElementById('refreshVBANBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshVBANSources);
    }
    
    // Vérifier l'existence de settings avant de l'utiliser
    if (typeof settings !== 'undefined') {
        // Charger les sources sauvegardées initiales
        displaySavedVBANSources(settings.saved_vban_sources || []);
    } else {
        console.error('Settings non définis');
        showNotification('Erreur de chargement des paramètres', 'error');
    }
    
    // Rafraîchir les sources détectées au chargement
    refreshVBANSources();

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
        if (document.getElementById('startButton').style.display !== 'inline-flex') {
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

    // Démarrer la détection
    startButton.addEventListener('click', async function() {
        const selectedMicro = document.getElementById('micro_source').value;
        const [deviceIndex, deviceName] = selectedMicro.split('|');
        const selectedVBAN = document.getElementById('vbanSourceSelect').value;

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
                stream_name: selectedVBAN ? selectedVBAN.split('_')[1] : "", // Extraire le nom du stream du VBAN ID
                ip: selectedVBAN ? selectedVBAN.split('_')[2] : "0.0.0.0",
                port: selectedVBAN ? parseInt(selectedVBAN.split('_')[3]) : 6980,
                webhook_url: "",
                enabled: selectedVBAN ? true : false
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
});
