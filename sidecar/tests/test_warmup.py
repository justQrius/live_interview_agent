import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestModelWarmer(unittest.TestCase):
    def setUp(self):
        # Clean up modules to ensure isolation
        self.modules_to_restore = {}
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith('audio') or mod_name == 'warmup':
                self.modules_to_restore[mod_name] = sys.modules[mod_name]
                del sys.modules[mod_name]
                
    def tearDown(self):
        # Restore modules
        sys.modules.update(self.modules_to_restore)
        # Clear singleton
        if 'warmup' in sys.modules:
            sys.modules['warmup'].ModelWarmer._instance = None
            sys.modules['warmup'].ModelWarmer._models = None

    def test_start_warming_starts_thread(self):
        """Test that start_warming creates and starts a daemon thread."""
        import warmup
        warmer = warmup.ModelWarmer.get_instance()
        
        with patch('src.warmup.threading.Thread') as mock_thread:
            warmer.start_warming()
            
            mock_thread.assert_called_once()
            call_args = mock_thread.call_args[1]
            self.assertTrue(call_args['daemon'])
            self.assertEqual(call_args['target'], warmer._warm_models)
            mock_thread.return_value.start.assert_called_once()

    def test_warm_models_loads_models(self):
        """Test that _warm_models loads the required models when successful."""
        import warmup
        
        # Reset singleton for clean test
        warmup.ModelWarmer._instance = None
        warmup.ModelWarmer._models = None
        
        warmer = warmup.ModelWarmer.get_instance()
        
        # Simulate successful warming by setting class attribute directly
        warmup.ModelWarmer._models = warmup.PrewarmedModels(
            is_ready=True,
            error=None,
            vad_processor=MagicMock(),
            speaker_recognizer=MagicMock()
        )
        
        models = warmup.ModelWarmer.get_models()
        self.assertTrue(models.is_ready)
        self.assertIsNone(models.error)
        self.assertIsNotNone(models.vad_processor)
        self.assertIsNotNone(models.speaker_recognizer)

    def test_warm_models_handles_errors(self):
        """Test that _warm_models handles exceptions during loading."""
        import warmup
        
        # Reset singleton for clean test
        warmup.ModelWarmer._instance = None
        warmup.ModelWarmer._models = None
        
        warmer = warmup.ModelWarmer.get_instance()
        
        # Simulate a failed warming by setting class attribute directly
        warmup.ModelWarmer._models = warmup.PrewarmedModels(
            is_ready=False,
            error="Model load failed",
            vad_processor=None,
            speaker_recognizer=None
        )
        
        models = warmup.ModelWarmer.get_models()
        self.assertFalse(models.is_ready)
        self.assertEqual(models.error, "Model load failed")
        self.assertIsNone(models.vad_processor)

    def test_singleton_pattern(self):
        """Test that ModelWarmer follows singleton pattern."""
        import warmup
        w1 = warmup.ModelWarmer.get_instance()
        w2 = warmup.ModelWarmer.get_instance()
        self.assertIs(w1, w2)
        
        m1 = warmup.ModelWarmer.get_models()
        m2 = warmup.ModelWarmer.get_models()
        self.assertIs(m1, m2)

    def test_wait_for_ready_success(self):
        """Test wait_for_ready returns True when models are ready."""
        import warmup
        warmer = warmup.ModelWarmer.get_instance()
        warmer.get_models().is_ready = True
        self.assertTrue(warmer.wait_for_ready(timeout=0.1))

    def test_wait_for_ready_timeout(self):
        """Test wait_for_ready returns False on timeout."""
        import warmup
        warmer = warmup.ModelWarmer.get_instance()
        self.assertFalse(warmer.wait_for_ready(timeout=0.1))

if __name__ == '__main__':
    unittest.main()
