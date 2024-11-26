// Ajouter au début du fichier
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;
    
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

// Ajouter la fonction refreshVBANSources
function refreshVBANSources() {
    const refreshBtn = document.getElementById('refreshVBAN');
    const sourceSelect = document.getElementById('vbanSourceSelect');
    
    if (!refreshBtn || !sourceSelect) return;
    
    // Ajouter la classe pour l'animation
    refreshBtn.classList.add('rotating');
    sourceSelect.innerHTML = '<option value="">Recherche des sources VBAN...</option>';
    
    fetch('/refresh_vban')
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(data => {
            console.log('Sources VBAN reçues:', data); // Debug log
            sourceSelect.innerHTML = '<option value="">Sélectionner une source VBAN</option>';
            
            if (data.sources && data.sources.length > 0) {
                data.sources.forEach(source => {
                    const option = document.createElement('option');
                    option.value = `vban_${source.name}_${source.ip}_${source.port}`;
                    option.textContent = `${source.name} (${source.ip}:${source.port}) - ${source.channels} canal${source.channels > 1 ? 'x' : ''} @ ${source.sample_rate}Hz`;
                    sourceSelect.appendChild(option);
                });
            } else {
                sourceSelect.innerHTML = '<option value="">Aucune source VBAN détectée</option>';
            }
        })
        .catch(error => {
            console.error('Erreur lors du rafraîchissement des sources VBAN:', error);
            sourceSelect.innerHTML = '<option value="">Erreur lors de la recherche des sources</option>';
        })
        .finally(() => {
            refreshBtn.classList.remove('rotating');
        });
}

let clapTimeout = null;

document.addEventListener('DOMContentLoaded', function() {
    const refreshBtn = document.getElementById('refreshVBAN');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshVBANSources);
        // Rafraîchir automatiquement au chargement
        setTimeout(refreshVBANSources, 1000); // Attendre 1s après le chargement
    }

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
