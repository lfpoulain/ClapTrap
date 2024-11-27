export function updateLabels(labels) {
    console.log('📝 Updating labels:', labels);
    const container = document.getElementById('detected_labels');
    if (!container) {
        console.error('❌ Labels container not found');
        return;
    }

    // Vider le conteneur
    container.innerHTML = '';

    // Ajouter les nouveaux labels
    labels.forEach(label => {
        const labelElement = document.createElement('span');
        labelElement.className = 'label';
        labelElement.innerHTML = `
            ${label.label}
            <span class="label-score">${Math.round(label.score * 100)}%</span>
        `;
        container.appendChild(labelElement);
    });
} 