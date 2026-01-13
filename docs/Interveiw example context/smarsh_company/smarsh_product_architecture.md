# Smarsh Product & Technical Architecture

## Communications Intelligence Platform Overview

The Smarsh product suite is unified under the **Communications Intelligence Platform**, designed to solve the "Velocity, Volume, and Variety" problem of modern communications data.

## Product Portfolio: The Unified Lifecycle

### 1. Capture: The Foundation of Fidelity

**Core Capability**: Ingestion of data from 80-100+ communication channels

#### Key Features
- **Native Format Preservation**: Unlike legacy solutions that convert all data to email format (EML), Smarsh captures data in its native format
  - Preserves threading, reactions, edits, emojis
  - Essential for legal defensibility (e.g., "thumbs up" emoji can be difference between conviction and acquittal)
  - Context-first approach for maximum fidelity

- **API-Based Ingestion**: Direct API integrations with platforms
  - Microsoft Teams, Slack, Zoom
  - Near real-time capture
  - Captures deleted messages seconds after sending

- **Supported Channels** (80-100+):
  - Email (Microsoft 365, Google Workspace)
  - Instant Messaging (Teams, Slack, Bloomberg, Symphony)
  - Mobile (SMS, WhatsApp, WeChat, Signal, Telegram)
  - Social Media (LinkedIn, Twitter, Facebook)
  - Voice (Trader turrets, Zoom audio)
  - Video (Zoom meetings, Microsoft Teams meetings)
  - Collaboration (SharePoint, OneDrive)

#### Technical Architecture
- Prioritizes direct API access over email-based forwarding
- Handles encrypted applications through specialized connectors
- Scalable ingestion pipeline supporting TB-scale daily data volumes

---

### 2. Archive: The Cloud-Native Repository

**Core Capability**: Immutable, petabyte-scale system of record

#### Key Features
- **Petabyte Scalability**: Architecture separates compute from storage
  - Effectively infinite storage capacity
  - No performance degradation as data volume grows
  - Elastic compute resources scale based on demand

- **High-Performance Search**:
  - Search across millions of records simultaneously
  - Support for varied content types (voice, text, video)
  - Results returned in seconds from petabytes of data
  - Parallel processing across thousands of compute nodes

- **Compliance & Immutability**:
  - SEC Rule 17a-4 compliant WORM (Write-Once-Read-Many) storage
  - Object locking prevents deletion/alteration before retention period expires
  - Even system administrators cannot tamper with archived records
  - Chain of custody maintained for legal defensibility

#### Technical Architecture
- Cloud-native design leveraging AWS infrastructure
- Triple-active redundancy across multiple AWS Availability Zones
- Continuous deployment via microservices architecture
- Zero-downtime updates and maintenance

---

### 3. Conduct: AI-Driven Surveillance

**Core Capability**: Behavioral monitoring using Digital Reasoning AI/ML assets

#### Key Features
- **Natural Language Processing (NLP)**:
  - Moves beyond keyword lexicons to understand intent
  - Example: "I guarantee I'll be late for dinner" vs. "I guarantee this stock will double"
  - Reduces false positives by up to 95% compared to lexicon-based systems
  - Context-aware analysis of sentiment and meaning

- **Behavioral Profiling**:
  - Establishes baseline "normal" behavior for each employee
  - Flags deviations: sudden spike in off-hours messaging, shift to encrypted channels
  - Anomaly detection for risk indicators

- **Entity Extraction**:
  - Identifies people, companies, locations within messages
  - Enables complex queries: "Show all conversations between Trader A and Company B regarding 'acquisition' where sentiment was secretive"

- **Voice Surveillance**:
  - Ingests and transcribes audio files using varying acoustic models
  - Applies text analytics to detect risks in spoken conversation
  - Voice Activity Detection filters silence and hold music

- **Risk Detection Types**:
  - Financial Crime: insider trading, market manipulation, front-running
  - Non-Financial Misconduct: harassment, toxic culture, discrimination
  - Regulatory Violations: unauthorized communications, record-keeping failures

#### Technical Architecture
- Leverages Digital Reasoning cognitive computing engine
- Real-time and batch processing pipelines
- Machine learning models continuously updated with new risk patterns
- Integration with HR and compliance systems for enriched context

---

### 4. Discovery: Legal Readiness

**Core Capability**: In-house Early Case Assessment and eDiscovery preparation

#### Key Features
- **Culling and Filtering**:
  - Powerful search filters narrow datasets efficiently
  - Example: Reduce 10 million messages to relevant 1,000
  - Dramatically reduces external legal spend

- **Export Capabilities**:
  - Industry-standard formats (EDRM XML, PST, NSF)
  - Seamless integration with downstream legal review tools (Relativity, etc.)
  - Maintains metadata and chain of custody

- **Context Preservation**:
  - Renders modern data (emojis, GIFs, edited messages) in readable format
  - Produces conversational thread views vs. disjointed spreadsheets
  - Courts increasingly demand this context-rich evidence format

#### Technical Architecture
- Built on same archive infrastructure ensuring consistent data
- Advanced filtering and tagging capabilities
- Role-based access controls for legal teams
- Audit trail of all discovery actions

---

## Platform Integration & Ecosystem

### Third-Party Integrations
- **Identity Management**: Azure AD, Okta for SSO
- **HR Systems**: Workday, SAP for employee data enrichment
- **Compliance Tools**: Integration with case management systems
- **Legal Platforms**: Export to Relativity, Everlaw, Logikcull

### API Capabilities
- RESTful APIs for programmatic access
- Webhook support for event-driven workflows
- Rate limiting and throttling management (e.g., Microsoft Graph API limits)
- OAuth authentication standards

---

## Technical Differentiators

### 1. Native Format vs. Legacy Conversion
| Aspect | Smarsh Native Format | Legacy Email Conversion |
|--------|---------------------|------------------------|
| Threading | Preserved exactly as appears in app | Lost or linearized |
| Reactions | Emojis and reactions maintained | Stripped or converted to text |
| Edits | Full edit history tracked | Only final version captured |
| Rich Media | Video, audio, images preserved | Often reduced to links |
| Context | Complete conversation flow | Fragmented messages |

### 2. Cloud-Native Architecture Advantages

| Feature | Cloud-Native (Smarsh) | Cloud-Washed (Legacy) |
|---------|----------------------|----------------------|
| **Scalability** | Elastic: Auto-scales based on load | Fixed: Limited by VM size |
| **Resiliency** | Triple-Active: Multi-AZ replication | Active-Passive: Manual failover |
| **Updates** | Continuous: Zero-downtime patches | Versioned: Scheduled maintenance windows |
| **Search Speed** | Parallel: Distributed across nodes | Linear: Degrades with data growth |

---

## Platform Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Search Latency | <5 seconds | Time to search across petabytes |
| Ingestion Throughput | 1TB+/day | Daily data capture capacity |
| System Uptime | 99.9% | Annual availability SLA |
| False Positive Reduction | 90-95% | vs. lexicon-based systems |

---

## Security Architecture

### Encryption
- **At Rest**: AES-256 encryption
- **In Transit**: TLS 1.2/1.3
- **Key Management**: AWS KMS integration

### Access Controls
- Role-Based Access Control (RBAC)
- Multi-Factor Authentication (MFA)
- Single Sign-On (SSO) support
- Audit logging of all access events

### Compliance Certifications
- SOC 2 Type II
- ISO 27001
- FINRA and SEC record-keeping requirements
- GDPR compliant for European operations

---

## Data Flow Architecture

```
External Sources → Capture Layer → Validation → Archive
     ↓                                              ↓
Mobile Apps                                    Conduct (AI Analysis)
Email Systems                                        ↓
IM Platforms                                   Risk Alerts
Voice Systems                                        ↓
                                              Discovery (Legal Review)
```

### Capture Layer Details
1. **Connection**: API or connector establishes secure link to source
2. **Authentication**: OAuth or service account credentials validated
3. **Streaming**: Data streamed in near real-time
4. **Normalization**: Converted to unified internal format
5. **Validation**: Integrity checks and deduplication
6. **Storage**: Immutable write to archive with encryption

### Processing Pipeline
1. **Archive Storage**: Data written to WORM storage
2. **Indexing**: Full-text search indices updated
3. **AI Analysis**: Conduct module analyzes for risks (async)
4. **Enrichment**: Metadata added from HR/compliance systems
5. **Alert Generation**: High-risk items flagged for review
6. **Dashboard Updates**: Real-time metrics updated
