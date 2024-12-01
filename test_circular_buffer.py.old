import unittest
import numpy as np
from circular_buffer import CircularAudioBuffer

class TestCircularAudioBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer_size = 1000
        self.channels = 2
        self.buffer = CircularAudioBuffer(self.buffer_size, self.channels)

    def test_initialization(self):
        self.assertEqual(self.buffer.buffer_size, self.buffer_size)
        self.assertEqual(self.buffer.channels, self.channels)
        self.assertEqual(self.buffer.write_pos, 0)
        self.assertEqual(self.buffer.filled, 0)

    def test_write_and_read_simple(self):
        # Créer des données de test
        test_data = np.random.rand(100, self.channels).astype(np.float32)
        
        # Écrire les données
        success = self.buffer.write(test_data)
        self.assertTrue(success)
        
        # Lire les données
        read_data = self.buffer.read(100)
        
        # Vérifier que les données lues sont identiques aux données écrites
        np.testing.assert_array_almost_equal(read_data, test_data)

    def test_write_overflow(self):
        # Créer des données plus grandes que le buffer
        test_data = np.random.rand(self.buffer_size + 500, self.channels).astype(np.float32)
        
        # Écrire les données
        success = self.buffer.write(test_data)
        self.assertTrue(success)
        
        # Vérifier que seuls les derniers échantillons sont conservés
        read_data = self.buffer.read(self.buffer_size)
        np.testing.assert_array_almost_equal(read_data, test_data[-self.buffer_size:])

    def test_circular_write(self):
        # Première écriture
        data1 = np.random.rand(500, self.channels).astype(np.float32)
        self.buffer.write(data1)
        
        # Deuxième écriture
        data2 = np.random.rand(700, self.channels).astype(np.float32)
        self.buffer.write(data2)
        
        # Lire les dernières données
        read_data = self.buffer.read(700)
        np.testing.assert_array_almost_equal(read_data, data2)

    def test_clear(self):
        # Écrire des données
        test_data = np.random.rand(500, self.channels).astype(np.float32)
        self.buffer.write(test_data)
        
        # Vider le buffer
        self.buffer.clear()
        
        # Vérifier que le buffer est vide
        self.assertEqual(self.buffer.filled, 0)
        self.assertEqual(self.buffer.write_pos, 0)
        np.testing.assert_array_equal(self.buffer.read(500), np.zeros((500, self.channels)))

    def test_buffer_level(self):
        # Buffer vide
        self.assertEqual(self.buffer.get_buffer_level(), 0.0)
        
        # Buffer à moitié plein
        test_data = np.random.rand(self.buffer_size // 2, self.channels).astype(np.float32)
        self.buffer.write(test_data)
        self.assertEqual(self.buffer.get_buffer_level(), 0.5)
        
        # Buffer plein
        test_data = np.random.rand(self.buffer_size, self.channels).astype(np.float32)
        self.buffer.write(test_data)
        self.assertEqual(self.buffer.get_buffer_level(), 1.0)

if __name__ == '__main__':
    unittest.main()
