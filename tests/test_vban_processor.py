import pytest
import numpy as np
from unittest.mock import Mock, patch
from mediapipe.tasks.python.components import containers
from mediapipe.tasks.python import audio
from vban_processor import VBANAudioProcessor

@pytest.fixture
def mock_socketio():
    return Mock()

@pytest.fixture
def mock_vban_detector():
    detector = Mock()
    detector.get_active_sources.return_value = ['192.168.1.10']
    return detector

@pytest.fixture
def mock_classifier():
    classifier = Mock()
    classifier.classify.return_value = Mock(
        classifications=[Mock(
            categories=[
                Mock(category_name="Clapping", score=0.7),
                Mock(category_name="Finger snapping", score=0.1)
            ]
        )]
    )
    return classifier

@pytest.fixture
def processor(mock_classifier):
    with patch('vban_processor.get_vban_detector') as mock_get_detector, \
         patch('mediapipe.tasks.python.audio.AudioClassifier.create_from_options', return_value=mock_classifier):
        mock_get_detector.return_value = Mock()
        processor = VBANAudioProcessor(
            ip='192.168.1.10',
            port=6980,
            stream_name='test_stream',
            webhook_url='http://test.webhook',
            score_threshold=0.2,
            delay=1.0
        )
        yield processor

def test_initialization(processor):
    """Test l'initialisation correcte du processeur VBAN."""
    assert processor.ip == '192.168.1.10'
    assert processor.port == 6980
    assert processor.stream_name == 'test_stream'
    assert processor.webhook_url == 'http://test.webhook'
    assert processor.score_threshold == 0.2
    assert processor.delay == 1.0
    assert processor.sample_rate == 16000
    assert not processor.is_running

def test_start_stop(processor):
    """Test le démarrage et l'arrêt du traitement."""
    # Test démarrage
    assert processor.start()
    assert processor.is_running
    
    # Test double démarrage
    assert not processor.start()  # Ne devrait pas redémarrer
    
    # Test arrêt
    assert processor.stop()
    assert not processor.is_running
    
    # Test double arrêt
    assert not processor.stop()  # Ne devrait pas re-arrêter

def test_preprocess_audio(processor):
    """Test le prétraitement des données audio."""
    # Test avec données mono
    mono_data = np.random.rand(16000)  # 1 seconde de données mono
    processed = processor.preprocess_audio(mono_data)
    assert isinstance(processed, containers.AudioData)
    assert isinstance(processed.audio_format, containers.AudioDataFormat)
    assert processed.audio_format.num_channels == 1
    
    # Vérification de la forme du buffer
    assert processed.buffer.shape[0] == processor.buffer_size  # Longueur correcte
    assert processed.buffer.shape[1] == 1  # Mono
    
    # Test avec données stéréo
    stereo_data = np.random.rand(16000, 2)  # 1 seconde de données stéréo
    processed = processor.preprocess_audio(stereo_data)
    assert isinstance(processed, containers.AudioData)
    assert processed.audio_format.num_channels == 1  # Devrait être converti en mono
    assert processed.buffer.shape[1] == 1  # Vérification que c'est bien mono
    
    # Test avec données courtes (padding)
    short_data = np.random.rand(8000)  # 0.5 seconde
    processed = processor.preprocess_audio(short_data)
    assert isinstance(processed, containers.AudioData)
    assert len(processed.buffer) == processor.buffer_size
    
    # Test avec données longues (troncature)
    long_data = np.random.rand(32000)  # 2 secondes
    processed = processor.preprocess_audio(long_data)
    assert isinstance(processed, containers.AudioData)
    assert len(processed.buffer) == processor.buffer_size

@patch('requests.post')
def test_notify_clap(mock_post, processor, mock_socketio):
    """Test les notifications de détection de clap."""
    processor.set_socketio(mock_socketio)
    mock_post.return_value.status_code = 200
    
    # Test notification websocket et webhook
    processor.notify_clap(0.8, 1234567890.0)
    
    # Vérifier la notification websocket
    mock_socketio.emit.assert_called_once()
    args = mock_socketio.emit.call_args[0]
    assert args[0] == 'clap'
    assert args[1]['source_id'] == 'vban-test_stream'
    assert args[1]['score'] == 0.8
    
    # Vérifier la notification webhook
    mock_post.assert_called_once_with('http://test.webhook')

def test_audio_callback(processor, mock_vban_detector):
    """Test le callback de traitement audio."""
    with patch.object(processor, 'detector', mock_vban_detector):
        with patch.object(processor, 'preprocess_audio') as mock_preprocess:
            with patch.object(processor, 'detect_claps') as mock_detect:
                # Test avec source valide
                audio_data = np.random.rand(16000)
                processor.audio_callback(audio_data, 1234567890.0)
                mock_preprocess.assert_called_once()
                mock_detect.assert_called_once()
                
                # Test avec source invalide
                mock_vban_detector.get_active_sources.return_value = ['192.168.1.11']
                processor.audio_callback(audio_data, 1234567890.0)
                # Ne devrait pas appeler preprocess_audio ou detect_claps
                assert mock_preprocess.call_count == 1
                assert mock_detect.call_count == 1

def test_classification_callback(processor, mock_socketio):
    """Test le callback de classification."""
    processor.set_socketio(mock_socketio)
    
    # Créer un mock de résultat de classification
    mock_category1 = Mock(category_name="Clapping", score=0.7)
    mock_category2 = Mock(category_name="Finger snapping", score=0.1)
    mock_classification = Mock(categories=[mock_category1, mock_category2])
    mock_result = Mock(classifications=[mock_classification])
    
    # Test avec un clap détecté
    processor._classification_callback(mock_result, 1234567890)
    mock_socketio.emit.assert_called_once()
    
    # Test avec délai (ne devrait pas émettre)
    processor._classification_callback(mock_result, 1234567891)
    assert mock_socketio.emit.call_count == 1  # Pas d'appel supplémentaire
    
    # Test après délai (devrait émettre)
    processor.last_clap_time = 0
    processor._classification_callback(mock_result, 1234567890)
    assert mock_socketio.emit.call_count == 2
