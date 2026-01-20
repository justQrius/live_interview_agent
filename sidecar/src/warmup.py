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
    local_whisper: Optional[object] = field(default=None, repr=False)  # faster-whisper model
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
            from src.audio.vad import VADProcessor
            from src.audio.diarization import SpeakerRecognizer
            
            with self._lock:
                logger.info("Loading Silero VAD model...")
                if self._models is None:
                    self._models = PrewarmedModels()
                    
                self._models.vad_processor = VADProcessor()
                
                logger.info("Loading ECAPA-TDNN model...")
                self._models.speaker_recognizer = SpeakerRecognizer()
                
                # Load faster-whisper model for local STT
                self._load_local_whisper()
                
                self._models.is_ready = True
                logger.info("All models pre-warmed successfully")
                
        except Exception as e:
            logger.error(f"Model pre-warming failed: {e}")
            if self._models is None:
                 self._models = PrewarmedModels()
            self._models.error = str(e)
    
    def _load_local_whisper(self) -> None:
        """
        Load faster-whisper model for local STT.
        
        Only loads if GPU is available for optimal performance.
        Falls back gracefully if not available.
        """
        try:
            from src.providers.stt.local_whisper import (
                LocalWhisperProvider, 
                _check_gpu_available
            )
            
            if _check_gpu_available():
                logger.info("Loading faster-whisper model (GPU detected)...")
                # Use large-v3-turbo for best speed/accuracy balance
                self._models.local_whisper = LocalWhisperProvider(
                    model_size="large-v3-turbo"
                )
                logger.info("faster-whisper model loaded successfully")
            else:
                logger.info("Skipping faster-whisper warmup (no GPU available)")
                
        except ImportError as e:
            logger.warning(f"faster-whisper not available for warmup: {e}")
        except Exception as e:
            logger.warning(f"Failed to pre-warm faster-whisper: {e}")
            # Non-fatal - provider will be created on demand if needed
    
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
