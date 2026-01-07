import logging
import threading
from typing import Optional
from dataclasses import dataclass, field
import sys

logger = logging.getLogger(__name__)

@dataclass
class PrewarmedModels:
    """Container for pre-warmed ML models."""
    vad_processor: Optional[object] = field(default=None, repr=False)
    speaker_recognizer: Optional[object] = field(default=None, repr=False)
    is_ready: bool = False
    error: Optional[str] = None

class ModelWarmer:
    """Pre-warms ML models in background thread."""
    
    _instance: Optional["ModelWarmer"] = None
    _models: Optional[PrewarmedModels] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._models = PrewarmedModels()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "ModelWarmer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_models(cls) -> PrewarmedModels:
        if cls._models is None:
            cls._models = PrewarmedModels()
        return cls._models
    
    def start_warming(self) -> None:
        """Start pre-warming models in background thread."""
        thread = threading.Thread(target=self._warm_models, daemon=True)
        thread.start()
        logger.info("Model pre-warming started in background")
    
    def _warm_models(self) -> None:
        """Load all ML models."""
        try:
            # Import here to avoid blocking main thread
            from audio.vad import VADProcessor
            from audio.diarization import SpeakerRecognizer
            
            with self._lock:
                logger.info("Loading Silero VAD model...")
                if self._models is None:
                    self._models = PrewarmedModels()
                    
                self._models.vad_processor = VADProcessor()
                
                logger.info("Loading ECAPA-TDNN model...")
                self._models.speaker_recognizer = SpeakerRecognizer()
                
                self._models.is_ready = True
                logger.info("All models pre-warmed successfully")
                
        except Exception as e:
            logger.error(f"Model pre-warming failed: {e}")
            if self._models is None:
                 self._models = PrewarmedModels()
            self._models.error = str(e)
    
    def wait_for_ready(self, timeout: float = 30.0) -> bool:
        """Wait for models to be ready."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if self._models and self._models.is_ready:
                return True
            if self._models and self._models.error:
                return False
            time.sleep(0.1)
        return False
