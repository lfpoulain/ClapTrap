import numpy as np
import pytest
from circular_buffer import CircularAudioBuffer

@pytest.fixture
def buffer():
    """Crée un buffer circulaire pour les tests."""
    return CircularAudioBuffer(buffer_size=1000, channels=1)

def test_initialization():
    """Test l'initialisation du buffer."""
    buffer = CircularAudioBuffer(buffer_size=1000, channels=2)
    assert buffer.buffer_size == 1000
    assert buffer.channels == 2
    assert buffer.buffer.shape == (1000, 2)
    assert buffer.write_pos == 0
    
def test_write_read(buffer):
    """Test l'écriture et la lecture du buffer."""
    # Test avec des données mono
    test_data = np.random.rand(500, 1).astype(np.float32)
    assert buffer.write(test_data)
    
    # Lecture des données
    read_data = buffer.read(500)
    assert read_data.shape == (500, 1)
    np.testing.assert_array_almost_equal(read_data, test_data)
    
def test_circular_write(buffer):
    """Test l'écriture circulaire."""
    # Première écriture
    data1 = np.ones((800, 1), dtype=np.float32)
    buffer.write(data1)
    
    # Vérification après la première écriture
    result1 = buffer.read(800)
    assert result1.shape == (800, 1)
    np.testing.assert_array_almost_equal(result1, np.ones((800, 1)))
    
    # Deuxième écriture qui doit wrap around
    data2 = np.zeros((400, 1), dtype=np.float32)
    buffer.write(data2)
    
    # Vérification après la deuxième écriture
    result2 = buffer.read(1000)
    assert result2.shape == (1000, 1)
    
    # Affichage pour le débogage
    print("\nContenu du buffer après les écritures:")
    print("Position d'écriture:", buffer.write_pos)
    print("Niveau de remplissage:", buffer.filled)
    print("Les 10 premiers échantillons:", result2[:10, 0])
    print("Les 10 derniers échantillons:", result2[-10:, 0])
    
    # Les 200 premiers échantillons doivent être des 1
    np.testing.assert_array_almost_equal(result2[:200, 0], np.ones(200))
    # Les 400 suivants doivent être des 0
    np.testing.assert_array_almost_equal(result2[200:600, 0], np.zeros(400))
    # Les 400 derniers doivent être des 1
    np.testing.assert_array_almost_equal(result2[600:], np.ones((400, 1)))
    
def test_overflow_handling(buffer):
    """Test la gestion du dépassement de buffer."""
    # Données plus grandes que le buffer
    big_data = np.random.rand(1500, 1).astype(np.float32)
    buffer.write(big_data)
    
    # On devrait avoir uniquement les 1000 derniers échantillons
    result = buffer.read(1000)
    np.testing.assert_array_almost_equal(result, big_data[-1000:])
    
def test_clear(buffer):
    """Test le nettoyage du buffer."""
    # Remplir le buffer
    data = np.ones((500, 1), dtype=np.float32)
    buffer.write(data)
    
    # Vider le buffer
    buffer.clear()
    
    # Vérifier que le buffer est vide
    result = buffer.read(500)
    np.testing.assert_array_almost_equal(result, np.zeros((500, 1)))
    assert buffer.write_pos == 0
    
def test_buffer_level(buffer):
    """Test le niveau de remplissage du buffer."""
    # Buffer vide
    assert buffer.get_buffer_level() == 0.0
    
    # Buffer à moitié plein
    data = np.ones((500, 1), dtype=np.float32)
    buffer.write(data)
    assert buffer.get_buffer_level() == 0.5
    
    # Buffer plein
    data = np.ones((1000, 1), dtype=np.float32)
    buffer.write(data)
    assert buffer.get_buffer_level() == 1.0
