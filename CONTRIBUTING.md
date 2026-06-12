# Contributing to Live Interview Agent

Thanks for your interest in contributing! This project is a cross-platform desktop application with a React/TypeScript UI, a Tauri (Rust) shell, and a Python AI sidecar. Pull requests, bug reports, and feature requests are all welcome.

## Quick links

- [Code of conduct](#code-of-conduct)
- [Filing bugs](#filing-bugs)
- [Suggesting features](#suggesting-features)
- [Submitting pull requests](#submitting-pull-requests)
- [Development setup](#development-setup)
- [Testing requirements](#testing-requirements)
- [Style guide](#style-guide)
- [Project layout](#project-layout)

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating you agree to abide by its terms. Be respectful, assume good faith, and focus on the work.

## Filing bugs

Open a [GitHub Issue](https://github.com/justQrius/live_interview_agent/issues) and include:

1. **What you expected to happen** and **what actually happened**
2. **Steps to reproduce** — minimal if possible
3. **Environment**: OS + version, Node version, Python version, whether you're using local Whisper (GPU/CPU) or a cloud STT provider
4. **Logs** — relevant excerpts from the sidecar log and the Tauri dev console. If the bug is audio-related, mention which input/output device you're using (loopback is platform-specific and varies by driver)
5. **Screenshots or screen recordings** when they help

If the bug involves an answer being wrong, off-topic, or hallucinated, please also include the **RAG manifest** (a JSON file the app can export) — that tells us which document chunks fed the answer and is invaluable for diagnosing groundedness regressions.

## Suggesting features

Open a GitHub Issue with the `enhancement` label. Describe:

- The problem you're trying to solve (not just the solution)
- Who benefits and in what scenario (interview, sales call, 1:1, etc.)
- Any rough ideas on implementation, if you have them
- Whether you'd be willing to submit a PR for it

Larger features — new providers, new LLM backends, new turn-detection strategies — are best discussed in an issue **before** you start a PR, so we can align on scope and architecture.

## Submitting pull requests

1. **Fork** the repository and create a feature branch from `master`:
   ```bash
   git checkout -b feature/short-description
   ```
2. **Write tests first** (TDD). All new code should land with tests. See [Testing requirements](#testing-requirements) below.
3. **Keep PRs focused** — one logical change per PR. Don't bundle drive-by refactors, renames, or reformatting with a feature.
4. **Run the full test suite** locally before pushing:
   ```bash
   npm run test              # Vitest (frontend)
   cd src-tauri && cargo test
   cd ../sidecar && pytest
   ```
5. **Update the README / docs** if your change is user-visible. The README's feature list, architecture diagram, and environment-variable table are user-facing.
6. **Reference any related issue** in the PR description (e.g. "Closes #123").
7. **Expect review** — a maintainer will review within a few days. Be ready to iterate.
8. **Squash or rebase** before merge to keep history clean.

## Development setup

```bash
# 1. Clone
git clone https://github.com/justQrius/live_interview_agent.git
cd live_interview_agent

# 2. Frontend
npm install

# 3. Python sidecar
cd sidecar
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
# Optional: NVIDIA GPU acceleration
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
cd ..

# 4. Run in dev mode (two terminals)
# Terminal 1:
cd sidecar && source venv/bin/activate  # or venv\Scripts\activate
python -m src.server

# Terminal 2:
npm run tauri dev
```

### Adding a new provider

The project uses a **Provider pattern** with a centralized `ProviderFactory`. To add a new STT, LLM, or search provider:

1. Implement the abstract base class in `sidecar/src/providers/{stt,llm,search}/<your_provider>.py`:
   - `STTProvider` for speech-to-text
   - `LLMProvider` for language models
   - `SearchProvider` for grounded web search
2. Register the provider type in `sidecar/src/providers/config.py` and instantiate it in `sidecar/src/providers/factory.py`.
3. Add a fallback entry to the chain in `ProviderFactory` if appropriate.
4. Add tests in `sidecar/tests/test_<your_provider>.py` using the same pattern as the existing provider tests.
5. Add the provider to the `README.md` configuration table and document any required environment variables.

### Adding a new STT / turn-detection mode

Streaming STT providers extend `StreamingSTTProvider` in `sidecar/src/providers/stt/streaming_base.py`. Turn detection has two layers:

- **Timing-based** (4-tier utterance accumulator) — modify `sidecar/src/classification/`
- **Semantic** (LiveKit) — modify `sidecar/src/livekit_integration/`

See `ENDPOINTING_PRIORITY_FIX.md` for the priority rules when both layers are active.

## Testing requirements

- **All tests must pass** before opening a PR:
  - `npm run test` — Vitest (frontend)
  - `cd src-tauri && cargo test` — Rust
  - `cd sidecar && pytest` — Python (66 test files)
- **Coverage targets**:
  - Python: **>80%** for core modules (`audio/`, `classification/`, `rag/`, `coaching/`, `providers/`)
  - TypeScript: **>70%** for components
  - Rust: unit tests for every Tauri command
- **TDD preferred**: write the failing test first, watch it fail for the right reason, then implement.
- For latency-sensitive changes, run the benchmark script and include before/after numbers in your PR:
  ```bash
  cd sidecar && python scripts/benchmark_latency.py
  python scripts/benchmark_livekit_turn_detection.py
  ```

## Style guide

### TypeScript / React
- Functional components with hooks
- **Zustand** for state management
- **Tailwind CSS** for styling
- **Named exports** for components
- `strict: true` TypeScript — no implicit `any`

### Rust (Tauri)
- Tauri commands live in `src-tauri/src/commands/`
- Platform-specific code in `utils/platform.rs`
- Use the `keyring` crate for secure API key storage — never store secrets in config files
- All errors returned as `Result<T, String>` from Tauri commands

### Python (sidecar)
- **Python 3.11+** with full type hints
- `async`/`await` for all I/O in the WebSocket server
- **Black** for formatting, **isort** for import ordering
- **Import convention**: always use the `src.` prefix (`from src.audio.vad import VADProcessor`, never `from audio.vad import …`)
- Follow existing `Provider` and `Factory` patterns when adding new services
- Tests live in `sidecar/tests/`, one file per module, named `test_<module>.py`

## Project layout

```
live_interview_agent/
├── src/                      # React frontend (TypeScript)
│   └── ui/
│       ├── components/       # 25+ components
│       ├── hooks/            # useWebSocket, useVAD
│       └── store/            # Zustand sessionStore
├── src-tauri/                # Tauri desktop shell (Rust)
│   └── src/
│       ├── commands/         # sidecar, config, window
│       └── utils/            # keyring, platform, storage
├── sidecar/                  # Python AI engine
│   └── src/
│       ├── server.py         # WebSocket IPC server
│       ├── audio/            # capture, VAD, diarization, noise reduction
│       ├── classification/   # question detector, reformulator, splitter, accumulator
│       ├── coaching/         # story recall, structure, consistency
│       ├── context/          # manager, chunker, gemini cache, file uploader
│       ├── extraction/       # pipeline, fact/story/profile extractors
│       ├── evaluation/       # groundedness scoring
│       ├── livekit_integration/  # semantic turn detection
│       ├── memory/           # SQLite store, models
│       ├── providers/        # STT, LLM, search providers + factory
│       ├── rag/              # engine, enhanced engine, embeddings, retrieval
│       └── storage/          # session store, exporter, RAG manifest
├── ARCHITECTURE.md           # Detailed system architecture
├── CONTRIBUTING.md           # This file
├── SECURITY.md               # Vulnerability reporting
└── README.md                 # User-facing documentation
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
