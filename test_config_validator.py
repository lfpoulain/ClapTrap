import pytest
from config_validator import validate_webhook_urls, ConfigValidationError

def test_valid_urls():
    config = {
        "microphone": {"webhook_url": "http://example.com/webhook"},
        "rtsp_sources": [
            {"name": "cam1", "webhook_url": "http://example.com/webhook1"},
            {"name": "cam2", "webhook_url": "https://example.com/webhook2"}
        ],
        "saved_vban_sources": [
            {"name": "source1", "webhook_url": "http://localhost:8123/webhook"}
        ],
        "vban": {"webhook_url": "http://192.168.1.100:8080/webhook"}
    }
    
    # Should not raise any exception
    validate_webhook_urls(config)

def test_invalid_urls():
    config = {
        "microphone": {"webhook_url": "invalid-url"},
        "rtsp_sources": [
            {"name": "cam1", "webhook_url": "not-a-url"}
        ]
    }
    
    with pytest.raises(ConfigValidationError):
        validate_webhook_urls(config)

def test_optional_urls():
    config = {
        "microphone": {"webhook_url": None},
        "rtsp_sources": [
            {"name": "cam1", "webhook_url": None}
        ],
        "vban": {}
    }
    
    # Should not raise any exception
    validate_webhook_urls(config) 