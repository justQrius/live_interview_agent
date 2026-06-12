# Security

Thank you for taking the time to disclose security issues responsibly. The maintainers of Live Interview Agent take reports seriously and will work with you to understand and address the issue quickly.

## Supported versions

| Version | Supported |
|---|---|
| `master` branch (latest) | ✅ Yes |
| Older releases | ⚠️ Best effort — please upgrade to `master` if possible |

This project is in active development. We do not maintain long-term backport branches. Security fixes land on `master` and are released as tagged versions.

## Reporting a vulnerability

**Please do not open a public GitHub Issue for security vulnerabilities.**

Report privately via one of the following channels:

1. **GitHub Security Advisories** (preferred): https://github.com/justQrius/live_interview_agent/security/advisories/new
2. **Email**: open a GitHub issue requesting the maintainer's contact email, or check the git commit history (`git log`) for an active maintainer address

A good report includes:

- A clear description of the issue and its impact
- Steps to reproduce, ideally with a minimal example
- The affected version / commit SHA
- Your assessment of severity (e.g. "audio capture reads from wrong device" vs. "RCE via crafted document upload")

You can expect:

- **Acknowledgement** within 72 hours
- **Initial triage** within 7 days
- **A fix or mitigation plan** for confirmed vulnerabilities, with timeline communicated to you
- **Credit** in the release notes / advisory, unless you ask to remain anonymous
- **Coordinated disclosure** — we ask that you don't publicly disclose the issue until a fix is released, typically within 90 days

## Threat model

Live Interview Agent is a **local desktop application**. Its security boundaries are:

| Boundary | Notes |
|---|---|
| **Audio capture** | Reads from microphone and system audio loopback. The loopback device is platform-specific; a malicious or misconfigured driver could feed crafted audio. STT and downstream stages treat audio as untrusted input. |
| **Document uploads** | Users upload their own documents (resume, JD, notes, Q&A, etc.). Files are parsed by `sidecar/src/context/parsers.py` and chunked. **A maliciously crafted PDF/DOCX could exploit parser bugs** — we treat parser code as security-sensitive. |
| **LLM prompts** | RAG-retrieved chunks are injected into LLM prompts. We do not currently defend against prompt injection from attacker-controlled documents. If you upload documents from untrusted sources, treat them like opening an email attachment. |
| **API keys** | Stored in the OS keychain (Windows Credential Manager, macOS Keychain, Linux Secret Service) via the `keyring` crate. Keys are never written to plaintext config files or environment variables that get committed. |
| **Network egress** | The app only makes outbound calls to providers you explicitly configure (Gemini, OpenAI, Anthropic, Deepgram, DuckDuckGo). No telemetry, no analytics, no auto-update check. |
| **WebSocket IPC** | The Python sidecar listens on `localhost:8765`. It is **not** intended to be exposed beyond the local machine; do not bind it to a public interface. |
| **Local files** | Sessions, documents, and the SQLite memory store are written to the OS app data directory. Other local processes running as your user can read them — same as any desktop app. |

### Out of scope

The following are **not** considered vulnerabilities:

- "Attacker with code execution on my machine can read my API keys" — true of any local app, not a vulnerability
- "Attacker can convince me to upload a malicious PDF" — social engineering, not a software bug
- "A prompt-injected document caused the LLM to produce a weird answer" — see prompt-injection note above; we plan mitigations but this is a known limitation of all RAG systems
- Theoretical attacks that require physical access to an unlocked machine

## Security-relevant dependencies

The application uses several third-party SDKs that handle sensitive data:

| SDK | Used for | Notes |
|---|---|---|
| `keyring` (Rust) | OS keychain access | Trusted, well-audited crate |
| `faster-whisper` | Local STT | Runs entirely on-device |
| `google-genai` | Gemini LLM / search / caching | Outbound to Google APIs |
| `openai` | OpenAI LLM | Outbound to OpenAI APIs |
| `anthropic` | Anthropic LLM | Outbound to Anthropic APIs |
| `deepgram-sdk` | Streaming STT | Outbound to Deepgram APIs |
| `pypdf`, `python-docx` | Document parsing | **Treated as security-sensitive** — please report parser crashes or weird behavior |
| `chromadb` | Local vector store | Local-only; no network |

We run `cargo audit` and `pip-audit` periodically. If you find a vulnerable transitive dependency, please report it.

## Hall-of-fame

There is no public hall-of-fame yet. Researchers who report valid vulnerabilities will be credited in the corresponding GitHub Security Advisory (unless they prefer to remain anonymous).
