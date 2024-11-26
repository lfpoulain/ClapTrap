function refreshVBANSources() {
    const refreshBtn = document.getElementById('refreshVBAN');
    const sourcesList = document.getElementById('vbanSourcesList');
    const sourceSelect = document.getElementById('vbanSourceSelect');
    
    if (!refreshBtn || !sourcesList) return;
    
    // Ajouter la classe pour l'animation
    refreshBtn.classList.add('rotating');
    sourcesList.innerHTML = '<p class="no-sources">Recherche des sources VBAN...</p>';
    
    fetch('/refresh_vban')
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(data => {
            console.log('Sources VBAN reçues:', data); // Debug log
            sourcesList.innerHTML = ''; // Vider la liste actuelle
            sourceSelect.innerHTML = '<option value="">Sélectionner une source VBAN</option>';
            
            if (data.sources && data.sources.length > 0) {
                data.sources.forEach(source => {
                    // Créer l'élément de liste
                    const sourceElement = document.createElement('div');
                    sourceElement.className = 'vban-source';
                    sourceElement.innerHTML = `
                        <div>
                            <strong>${source.name}</strong>
                            <div class="vban-source-info">
                                ${source.ip}:${source.port} - 
                                ${source.channels} canal${source.channels > 1 ? 'x' : ''} @ ${source.sample_rate}Hz
                            </div>
                        </div>
                    `;
                    sourcesList.appendChild(sourceElement);
                    
                    // Ajouter l'option au select
                    const option = document.createElement('option');
                    option.value = source.id;
                    option.textContent = `${source.name} (${source.ip}:${source.port})`;
                    sourceSelect.appendChild(option);
                });
                
                sourceSelect.style.display = 'block';
            } else {
                sourcesList.innerHTML = '<p class="no-sources">Aucune source VBAN détectée</p>';
                sourceSelect.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Erreur lors du rafraîchissement des sources VBAN:', error);
            sourcesList.innerHTML = '<p class="no-sources">Erreur lors de la recherche des sources</p>';
            sourceSelect.style.display = 'none';
        })
        .finally(() => {
            refreshBtn.classList.remove('rotating');
        });
}

// Ajouter l'écouteur d'événement une fois le DOM chargé
document.addEventListener('DOMContentLoaded', function() {
    const refreshBtn = document.getElementById('refreshVBAN');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshVBANSources);
        // Rafraîchir automatiquement au chargement
        setTimeout(refreshVBANSources, 1000); // Attendre 1s après le chargement
    }
});
