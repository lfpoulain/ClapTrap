document.getElementById('refresh_vban').addEventListener('click', function() {
    const button = this;
    const select = document.getElementById('audio_source');
    
    // Ajouter la classe pour l'animation
    button.classList.add('refreshing');
    
    // Sauvegarder la valeur sélectionnée actuelle
    const currentValue = select.value;
    
    fetch('/refresh_vban_sources')
        .then(response => response.json())
        .then(data => {
            // Supprimer les anciennes sources VBAN
            Array.from(select.options).forEach(option => {
                if (option.value.startsWith('vban://')) {
                    option.remove();
                }
            });
            
            // Ajouter les nouvelles sources VBAN
            data.sources.forEach(source => {
                const option = new Option(source.name, source.url);
                select.add(option);
            });
            
            // Restaurer la sélection si possible
            if (Array.from(select.options).some(opt => opt.value === currentValue)) {
                select.value = currentValue;
            }
        })
        .catch(error => {
            console.error('Erreur lors du rafraîchissement des sources VBAN:', error);
        })
        .finally(() => {
            // Retirer la classe d'animation
            button.classList.remove('refreshing');
        });
});

// Fonction pour afficher les notifications
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// Fonction pour mettre à jour l'état des boutons
function updateButtonState(isRunning) {
    console.log('Updating button state:', isRunning);
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    
    if (startButton && stopButton) {
        if (isRunning) {
            console.log('Setting to running state');
            startButton.style.display = 'none';
            stopButton.style.display = 'block';
        } else {
            console.log('Setting to stopped state');
            startButton.style.display = 'block';
            stopButton.style.display = 'none';
        }
        startButton.disabled = false;
        stopButton.disabled = false;
    }
}

// Fonction pour valider les paramètres
function validateSettings(settings) {
    // Validation de la source audio
    if (!settings.audio_source) {
        showNotification('La source audio est requise', 'error');
        return false;
    }

    // Validation du threshold (entre 0 et 1)
    const threshold = parseFloat(settings.threshold);
    if (isNaN(threshold) || threshold < 0 || threshold > 1) {
        showNotification('La précision doit être un nombre entre 0 et 1', 'error');
        return false;
    }

    // Validation du délai (positif)
    const delay = parseFloat(settings.delay);
    if (isNaN(delay) || delay < 0) {
        showNotification('Le délai doit être un nombre positif', 'error');
        return false;
    }

    // Validation du webhook URL (optionnel)
    if (settings.webhook_url) {
        try {
            new URL(settings.webhook_url);
            if (!settings.webhook_url.startsWith('http://') && !settings.webhook_url.startsWith('https://')) {
                showNotification('L\'URL du webhook doit commencer par http:// ou https://', 'error');
                return false;
            }
        } catch (e) {
            showNotification('L\'URL du webhook n\'est pas valide', 'error');
            return false;
        }
    }

    return true;
}

// Fonction pour vérifier les paramètres sauvegardés
async function verifySettings(originalSettings) {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        
        if (data.settings) {  // Si le serveur renvoie les paramètres actuels
            console.log('Vérification des paramètres:');
            console.log('Paramètres originaux:', originalSettings);
            console.log('Paramètres sauvegardés:', data.settings);
            
            // Vérifier chaque paramètre
            const fields = ['audio_source', 'threshold', 'delay', 'webhook_url'];
            for (const field of fields) {
                if (originalSettings[field] !== data.settings[field]) {
                    console.error(`Différence détectée pour ${field}:`, {
                        original: originalSettings[field],
                        saved: data.settings[field]
                    });
                }
            }
        }
    } catch (error) {
        console.error('Erreur lors de la vérification des paramètres:', error);
    }
}

// Fonction pour démarrer la détection avec gestion d'erreurs améliorée
async function startDetection(event) {
    if (event) event.preventDefault();
    console.log('Starting detection...');
    
    const settings = {
        audio_source: document.getElementById('audio_source').value,
        threshold: document.getElementById('threshold').value,
        delay: document.getElementById('delay').value,
        webhook_url: document.getElementById('webhook_url').value
    };

    console.log('Paramètres à sauvegarder:', settings);

    // Valider les paramètres avant de continuer
    if (!validateSettings(settings)) {
        return;
    }

    // Sauvegarder l'état des boutons pour pouvoir les restaurer en cas d'erreur
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const originalStartDisplay = startButton.style.display;
    const originalStopDisplay = stopButton.style.display;

    try {
        // Désactiver les boutons pendant le traitement
        startButton.disabled = true;
        stopButton.disabled = true;

        // Mettre à jour l'interface immédiatement
        updateButtonState(true);
        showNotification('Démarrage de la détection...');
        
        const response = await fetch('/start_detection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        const data = await response.json();
        console.log('Start detection response:', data);
        
        if (response.ok) {
            showNotification('Détection démarrée avec succès');
            // Vérifier que les paramètres ont été correctement sauvegardés
            await verifySettings(settings);
        } else {
            // En cas d'erreur, restaurer l'état précédent
            startButton.style.display = originalStartDisplay;
            stopButton.style.display = originalStopDisplay;
            showNotification(data.message || 'Erreur lors du démarrage de la détection', 'error');
            console.error('Erreur serveur:', data.message);
        }
    } catch (error) {
        console.error('Erreur:', error);
        // En cas d'erreur, restaurer l'état précédent
        startButton.style.display = originalStartDisplay;
        stopButton.style.display = originalStopDisplay;
        showNotification('Erreur lors du démarrage de la détection', 'error');
    } finally {
        // Réactiver les boutons
        startButton.disabled = false;
        stopButton.disabled = false;
    }
}

// Fonction pour arrêter la détection
async function stopDetection(event) {
    if (event) event.preventDefault();
    console.log('Stopping detection...');
    
    // Mettre à jour l'interface immédiatement
    updateButtonState(false);
    showNotification('Détection arrêtée avec succès');
    
    try {
        const response = await fetch('/stop_detection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        console.log('Stop detection response:', data);
        
        if (!response.ok) {
            // En cas d'erreur, revenir à l'état précédent
            updateButtonState(true);
            showNotification(data.message || 'Erreur lors de l\'arrêt de la détection', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        // En cas d'erreur, revenir à l'état précédent
        updateButtonState(true);
        showNotification('Erreur lors de l\'arrêt de la détection', 'error');
    }
}

// Fonction pour exécuter les tests
async function runTests() {
    try {
        showNotification('Exécution des tests...');
        
        const response = await fetch('/run_tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        
        if (response.ok) {
            showNotification('Tests terminés, vérifiez les logs du serveur');
            console.log('Tests terminés:', data.message);
        } else {
            showNotification('Erreur lors de l\'exécution des tests', 'error');
            console.error('Erreur lors des tests:', data.message);
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur lors de l\'exécution des tests', 'error');
    }
}

// Attacher les événements aux boutons
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, attaching event listeners...');
    
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');

    if (startButton) {
        startButton.onclick = startDetection;
        console.log('Start button listener attached');
    }

    if (stopButton) {
        stopButton.onclick = stopDetection;
        console.log('Stop button listener attached');
    }

    // Vérifier l'état initial
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            console.log('Initial status:', data);
            updateButtonState(data.running);
        })
        .catch(error => {
            console.error('Error checking status:', error);
        });
});
