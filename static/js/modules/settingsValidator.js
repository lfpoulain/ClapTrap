// Schéma de validation des paramètres
const settingsSchema = {
    global: {
        required: ['threshold', 'delay'],
        defaults: {
            threshold: '0.5',
            delay: '1.0'
        }
    },
    microphone: {
        required: ['enabled', 'webhook_url', 'audio_source', 'device_index'],
        defaults: {
            enabled: false,
            webhook_url: '',
            audio_source: 'default',
            device_index: '0'
        }
    },
    rtsp_sources: {
        type: 'array',
        itemSchema: {
            required: ['id', 'name', 'url', 'webhook_url', 'enabled'],
            defaults: {
                webhook_url: '',
                enabled: false,
                url: ''
            }
        }
    },
    saved_vban_sources: {
        type: 'array',
        itemSchema: {
            required: ['name', 'ip', 'port', 'stream_name', 'webhook_url', 'enabled'],
            defaults: {
                webhook_url: '',
                enabled: false,
                port: 6980,
                stream_name: ''
            }
        }
    },
    vban: {
        required: ['stream_name', 'ip', 'port', 'webhook_url', 'enabled'],
        defaults: {
            stream_name: '',
            ip: '0.0.0.0',
            port: 6980,
            webhook_url: '',
            enabled: false
        }
    }
};

// Valide et complète les paramètres manquants
export function validateSettings(settings) {
    console.log('🔍 Validation - Paramètres reçus:', settings);
    const validatedSettings = { ...settings };
    const errors = [];

    // Valider chaque section
    Object.entries(settingsSchema).forEach(([section, schema]) => {
        if (!validatedSettings[section]) {
            if (section === 'rtsp_sources') {
                // Préserver les sources RTSP existantes
                validatedSettings[section] = settings[section] || [];
                console.log('🔍 Validation - Préservation des sources RTSP:', validatedSettings[section]);
            } else {
                validatedSettings[section] = schema.type === 'array' ? [] : {};
            }
        }

        if (schema.type === 'array') {
            // Pour les tableaux (comme rtsp_sources), préserver les valeurs existantes
            if (!Array.isArray(validatedSettings[section])) {
                validatedSettings[section] = [];
            }
            // Ne pas réinitialiser les tableaux existants
            console.log(`🔍 Validation - Tableau ${section}:`, validatedSettings[section]);
        } else {
            // Pour les autres sections, vérifier les champs requis
            if (schema.required) {
                schema.required.forEach(field => {
                    if (!validatedSettings[section][field] && validatedSettings[section][field] !== false) {
                        validatedSettings[section][field] = schema.defaults[field];
                        errors.push(`Champ manquant ${section}.${field}, valeur par défaut utilisée`);
                    }
                });
            }
        }
    });

    console.log('🔍 Validation - Paramètres validés:', validatedSettings);
    return {
        settings: validatedSettings,
        errors,
        isValid: true
    };
}

// Compare les paramètres actuels avec ceux de l'interface
export function compareWithDOMValues(settings) {
    const differences = [];

    // Vérifier les valeurs globales
    const threshold = document.getElementById('threshold');
    const delay = document.getElementById('delay');
    if (threshold && settings.global.threshold !== threshold.value) {
        differences.push(`Seuil: ${settings.global.threshold} ≠ ${threshold.value}`);
    }
    if (delay && settings.global.delay !== delay.value) {
        differences.push(`Délai: ${settings.global.delay} ≠ ${delay.value}`);
    }

    // Vérifier les paramètres du microphone
    const micEnabled = document.getElementById('webhook-mic-enabled');
    const micUrl = document.getElementById('webhook-mic-url');
    const micSource = document.getElementById('micro_source');
    
    if (micEnabled && settings.microphone.enabled !== micEnabled.checked) {
        differences.push(`Microphone activé: ${settings.microphone.enabled} ≠ ${micEnabled.checked}`);
    }
    if (micUrl && settings.microphone.webhook_url !== micUrl.value) {
        differences.push(`URL webhook microphone: ${settings.microphone.webhook_url} ≠ ${micUrl.value}`);
    }
    if (micSource && settings.microphone.audio_source !== micSource.value.split('|')[1]) {
        differences.push(`Source audio: ${settings.microphone.audio_source} ≠ ${micSource.value.split('|')[1]}`);
    }

    return {
        hasDifferences: differences.length > 0,
        differences: differences
    };
}

// Vérifie si tous les champs requis sont présents dans l'interface
export function validateDOM() {
    const missingElements = [];
    const requiredElements = [
        'threshold',
        'delay',
        'webhook-mic-enabled',
        'webhook-mic-url',
        'micro_source'
    ];

    requiredElements.forEach(id => {
        if (!document.getElementById(id)) {
            missingElements.push(id);
        }
    });

    return {
        isValid: missingElements.length === 0,
        missingElements: missingElements
    };
}
