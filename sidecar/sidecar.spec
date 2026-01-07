# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Live Interview Agent sidecar.

This bundles the Python sidecar into a single executable that includes:
- WebSocket server (server.py)
- Audio capture and VAD processing
- Gemini STT/LLM clients
- ChromaDB vector store
- SpeechBrain speaker diarization

Usage:
    pyinstaller sidecar.spec

Output:
    dist/sidecar-server (or sidecar-server.exe on Windows)
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the sidecar directory
SIDECAR_DIR = Path(SPECPATH)
SRC_DIR = SIDECAR_DIR / "src"

# Determine platform-specific settings
is_windows = sys.platform == "win32"
is_macos = sys.platform == "darwin"
is_linux = sys.platform.startswith("linux")

# Executable name
exe_name = "sidecar-server.exe" if is_windows else "sidecar-server"

# Collect hidden imports that PyInstaller often misses
hidden_imports = [
    # WebSocket server
    "websockets",
    "websockets.asyncio",
    "websockets.asyncio.server",
    "websockets.exceptions",
    
    # Torch and related
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "torch.jit",
    "torch.utils",
    "torchaudio",
    "torchaudio.transforms",
    "torchaudio.functional",
    
    # SpeechBrain for speaker diarization
    "speechbrain",
    "speechbrain.pretrained",
    "speechbrain.pretrained.interfaces",
    "speechbrain.inference.speaker",
    "hyperpyyaml",
    
    # Google Generative AI (Gemini)
    "google.generativeai",
    "google.generativeai.types",
    "google.ai.generativelanguage",
    "google.api_core",
    "google.auth",
    "google.protobuf",
    "grpc",
    
    # ChromaDB
    "chromadb",
    "chromadb.api",
    "chromadb.config",
    "chromadb.db",
    "chromadb.db.impl",
    "chromadb.db.impl.sqlite",
    "chromadb.segment",
    "chromadb.telemetry",
    "chromadb.utils",
    "chromadb.utils.embedding_functions",
    "hnswlib",
    "pysqlite3",
    
    # Document processing
    "pypdf",
    "docx",
    "bs4",
    "lxml",
    
    # Audio processing
    "numpy",
    "scipy",
    "scipy.io",
    "scipy.io.wavfile",
    "scipy.signal",
    "noisereduce",
    
    # Silero VAD
    "silero_vad",
    
    # Standard library extensions
    "asyncio",
    "concurrent.futures",
    "multiprocessing",
    "queue",
    "dataclasses",
    "typing",
    "json",
    "base64",
    "logging",
    
    # Platform-specific audio
    *( ["pyaudiowpatch", "pyaudio"] if is_windows else ["sounddevice"] ),
    
    # Hugging Face (for model downloads)
    "huggingface_hub",
    "huggingface_hub.utils",
    "huggingface_hub.file_download",
]

# Collect all submodules for complex packages
hidden_imports += collect_submodules("torch")
hidden_imports += collect_submodules("torchaudio")
hidden_imports += collect_submodules("speechbrain")
hidden_imports += collect_submodules("chromadb")
hidden_imports += collect_submodules("google.generativeai")

# Remove duplicates
hidden_imports = list(set(hidden_imports))

# Collect data files (models, configs, etc.)
datas = []

# Collect torch data files (needed for JIT)
datas += collect_data_files("torch")

# Collect torchaudio data files
try:
    datas += collect_data_files("torchaudio")
except Exception:
    pass

# Collect SpeechBrain data
try:
    datas += collect_data_files("speechbrain")
except Exception:
    pass

# Collect Silero VAD model data
try:
    datas += collect_data_files("silero_vad")
except Exception:
    pass

# Collect ChromaDB data
try:
    datas += collect_data_files("chromadb")
except Exception:
    pass

# Collect our source modules as data (for dynamic imports)
datas += [
    (str(SRC_DIR / "audio"), "audio"),
    (str(SRC_DIR / "stt"), "stt"),
    (str(SRC_DIR / "context"), "context"),
    (str(SRC_DIR / "rag"), "rag"),
    (str(SRC_DIR / "llm"), "llm"),
    (str(SRC_DIR / "protocol.py"), "."),
]

# Binary dependencies
binaries = []

# On Windows, collect any DLLs needed
if is_windows:
    # PyAudio/PortAudio DLLs are usually bundled automatically
    pass

# Analysis
a = Analysis(
    [str(SRC_DIR / "server.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude dev/test dependencies to reduce size
        "pytest",
        "pytest_asyncio",
        "pytest_mock",
        "pytest_cov",
        "black",
        "isort",
        "mypy",
        "flake8",
        # Exclude tkinter (not needed)
        "tkinter",
        "_tkinter",
        "tcl",
        "tk",
        # Exclude matplotlib if not used
        "matplotlib",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name.replace(".exe", "") if is_windows else exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logging output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Note: We're not creating a COLLECT or BUNDLE since we want a single-file executable
# The --onefile mode is achieved by including everything in the EXE block
