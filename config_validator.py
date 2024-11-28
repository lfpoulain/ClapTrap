from url_validator import is_valid_url

class ConfigValidationError(Exception):
    pass

def validate_webhook_urls(config):
    """
    Validate all webhook URLs in the configuration.
    Raises ConfigValidationError if any URL is invalid.
    """
    errors = []
    
    # Validate microphone webhook
    if config.get('microphone', {}).get('webhook_url'):
        if not is_valid_url(config['microphone']['webhook_url']):
            errors.append("Invalid microphone webhook URL")
    
    # Validate RTSP sources webhooks
    for source in config.get('rtsp_sources', []):
        if source.get('webhook_url') and not is_valid_url(source['webhook_url']):
            errors.append(f"Invalid webhook URL for RTSP source '{source.get('name', 'unnamed')}'")
    
    # Validate VBAN saved sources webhooks
    for source in config.get('saved_vban_sources', []):
        if source.get('webhook_url') and not is_valid_url(source['webhook_url']):
            errors.append(f"Invalid webhook URL for VBAN source '{source.get('name', 'unnamed')}'")
    
    # Validate global VBAN webhook
    if config.get('vban', {}).get('webhook_url'):
        if not is_valid_url(config['vban']['webhook_url']):
            errors.append("Invalid VBAN webhook URL")
    
    if errors:
        raise ConfigValidationError("\n".join(errors)) 