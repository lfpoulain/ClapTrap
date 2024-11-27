export function showNotification(message, type = 'success') {
    const notification = document.getElementById(type);
    if (!notification) {
        console.error('Element notification non trouvé');
        return;
    }
    
    notification.textContent = message;
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

export function showSuccess(message) {
    showNotification(message, 'success');
}

export function showError(message) {
    showNotification(message, 'error');
} 