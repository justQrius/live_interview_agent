# Live Interview Agent

A cross-platform desktop application that provides real-time AI assistance during job interviews. This tool leverages a sidecar architecture combining a robust Tauri (Rust) backend with a powerful Python AI engine to deliver real-time speech-to-text, context-aware answers, and seamless OS integration.

## Key Features

- **Multi-Provider Support**: Choose from **Groq** (ultra-fast), **Deepgram**, or **OpenAI** for STT, and **OpenAI** or **Anthropic** for LLM reasoning.
- **Intelligent Question Detection**: Real-time classification of interview questions (behavioral, technical, etc.) with <10ms latency.
- **Conversational Intelligence**: Advanced query reformulation and question splitting for complex, multi-part, or follow-up interview questions.
- **Enhanced Context Preparation**: Multi-document support (Resume, JD, Company Info) with automated pre-interview briefing and STAR story generation.
- **Low-Latency Architecture**:
  - **Browser-based VAD**: Filters silence locally, reducing server traffic by >60%.
  - **Model Pre-warming**: ML models load at app startup for <1s session starts.
  - **Intelligence Pipeline**: Optimized classification and reformulation with <15ms combined overhead.
  - **Parallel Processing**: Audio pipeline optimized for <1.5s end-to-end latency.
- **Real-time Audio Capture & Transcription**: High-accuracy speech recognition with speaker diarization.
- **Context-Aware Assistance**: RAG-powered answers grounded in your resume and job description.
- **Stealth Mode**: Invisible during screen shares.
- **Cross-Platform**: Windows, macOS, and Linux support.

## Getting Started

### Prerequisites

- **Node.js**: v20+
- **Rust**: v1.75+
- **Python**: v3.11+
- **OS-Specific Build Tools**:
  - *Windows*: Visual Studio C++ Build Tools
  - *macOS*: Xcode Command Line Tools
  - *Linux*: `build-essential`, `libwebkit2gtk-4.0-dev`, `libssl-dev`

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/live_interview_agent.git
    cd live_interview_agent
    ```

2.  **Install Frontend Dependencies**:
    ```bash
    npm install
    ```

3.  **Install Python Sidecar Dependencies**:
    ```bash
    cd sidecar
    python -m venv venv
    
    # Activate virtual environment
    # Windows: venv\Scripts\activate #source venv/Scripts/activate (if bash)
    # macOS/Linux: source venv/bin/activate

    pip install -r requirements.txt
    cd ..
    ```

### Running the Application

In development, you need to run both the Tauri frontend/backend and the Python sidecar process.

1. **Start the Python Sidecar** (in a separate terminal):
    ```bash
    cd sidecar
    # Activate virtual environment first (see installation steps above)
    python src/server.py
    ```

2. **Start the Tauri App**:
    ```bash
    npm run tauri dev
    ```

To build the application for production (which bundles the sidecar):

```bash
npm run tauri build
```

## Configuration

1.  Launch the app and click the **Settings** icon.
2.  Enter API keys for your preferred providers:
    -   **Groq**: Ultra-fast transcription (Recommended).
    -   **OpenAI**: GPT-4o for high-quality answers.
    -   **Anthropic**: Claude 3.5 Sonnet for complex reasoning.
    -   **Deepgram**: Alternative high-speed STT.
    -   **Gemini**: Fallback provider.
3.  Select your preferred **STT** and **LLM** providers from the dropdowns.
4.  Keys are stored securely in your OS keychain.

## Architecture

```mermaid
graph TB
    subgraph "Tauri App"
        UI[React UI]
        BrowserVAD[Browser VAD<br/>(ONNX)]
        Config[Config Store]
    end

    subgraph "Python Sidecar"
        Server[WebSocket Server]
        Factory[Provider Factory]
        
        subgraph "Providers"
            Groq[Groq STT]
            Deepgram[Deepgram STT]
            OpenAI[OpenAI STT/LLM]
            Anthropic[Anthropic LLM]
            Gemini[Gemini STT/LLM]
        end
        
        Models[Pre-warmed Models<br/>(VAD/Diarization)]
        
        subgraph "Intelligence Pipeline"
            Detector[Question Detector]
            Reformulator[Query Reformulator]
            Splitter[Question Splitter]
        end
        
        RAG[RAG Engine]
    end

    UI --> BrowserVAD
    BrowserVAD -->|Speech Only| Server
    Server --> Models
    Models --> Factory
    Factory --> Providers
    Providers --> Detector
    Detector --> Reformulator
    Reformulator --> Splitter
    Splitter --> RAG
    RAG --> Providers
```

## Development

### Project Structure

- **`src/`**: React frontend (UI, Hooks, VAD, Context UI).
- **`src-tauri/`**: Rust backend (OS integration, Keyring).
- **`sidecar/`**: Python engine (Audio processing, Classification, Providers, RAG).
- **`_prism/`**: SDLC documentation.

### Testing

- **Frontend**: `npm run test`
- **Backend**: `cd src-tauri && cargo test`
- **Sidecar**: `cd sidecar && pytest`
- **E2E**: `cd sidecar && pytest tests/test_e2e_scenarios.py`

## License

MIT License - see [LICENSE](LICENSE) for details.
