# Smarsh AI & Machine Learning Capabilities

## Overview: Augmented Intelligence Philosophy

Smarsh's AI/ML approach centers on **Augmented Intelligence**—enhancing human analyst capabilities rather than replacing them. The core technology stems from the November 2020 acquisition of Digital Reasoning, a market leader in cognitive computing and NLP widely used by intelligence agencies and top-tier investment banks.

---

## Core AI/ML Technologies

### Natural Language Processing (NLP)

#### Beyond Keywords: Intent Understanding
**Legacy Lexicon Approach**:
- Keyword matching: Flag word "guarantee"
- Result: Thousands of false positives for phrases like "I guarantee I'll be late for dinner"

**Smarsh NLP Approach**:
- Context-aware analysis understands intent
- Flags: "I guarantee this stock will double" (market manipulation risk)
- Ignores: "I guarantee I'll be late for dinner" (no compliance risk)
- **Result**: 90-95% reduction in false positives

#### Sentiment Analysis
- Detects emotional tone: secretive, urgent, anxious, evasive
- Example query: "Show conversations where sentiment shifted from professional to secretive"
- Identifies attempts to obfuscate or hide information

#### Entity Extraction & Relationship Mapping
**Capabilities**:
- Identifies entities: People, companies, stock tickers, locations, dates
- Maps relationships between entities
- Tracks entity mentions across time and channels

**Advanced Query Example**:
"Show all conversations between Trader A and Company B regarding 'acquisition' where the sentiment was secretive AND occurred within 48 hours before Company B's stock price moved >5%"

---

### Behavioral Profiling & Anomaly Detection

#### Normal Behavior Baseline
**System Learning**:
- Establishes individual employee baseline over 90-day period
- Typical patterns: communication hours, channel preferences, contact frequency, message length

#### Deviation Detection
**Risk Indicators Flagged**:
1. **Channel Shift Anomaly**: Trader suddenly moves from monitored email to WhatsApp
2. **Temporal Anomaly**: High volume of messages at 2 AM (outside normal 8 AM - 6 PM pattern)
3. **Volume Spike**: 10x increase in communications with specific external contact
4. **Lexical Shift**: Sudden use of unusual terminology or coded language
5. **Deletion Pattern**: Rapid message sending followed by immediate deletion attempts

**Example Alert**:
"Employee X typically sends 50 emails/day. Today sent 300 WhatsApp messages to Contact Y, 80% outside business hours. This represents a 600% volume anomaly and channel shift. Probability of investigation-worthy behavior: 87%"

---

### Voice & Audio Intelligence

#### Audio Transcription Pipeline
1. **Ingestion**: Audio files from trader turrets, Zoom, recorded calls
2. **Transcription**: Amazon Transcribe with custom financial vocabulary
3. **Voice Activity Detection (VAD)**: Filters silence, hold music, non-speech
4. **Speaker Diarization**: Identifies who said what (Speaker 1, Speaker 2)
5. **Text Analytics**: Applies NLP to transcribed text

#### Voice-Specific Risk Detection
- **Acoustic Stress Analysis**: Detects vocal stress indicators during specific discussions
- **Interruption Patterns**: Identifies domineering behavior in compliance interviews
- **Hedge Language**: Flags evasive responses ("I think maybe possibly...")

---

### Generative AI Integration (2025-2026 Roadmap)

#### Use Cases in Development

**1. Intelligent Alert Triage (Level 1 Analyst Automation)**
- **Current State**: Human analysts review every alert, 95% false positives
- **AI Solution**: LLM reviews alert, provides preliminary risk assessment
- **Output**: "Low Risk - Birthday gift discussion, no policy violation" vs. "High Risk - Possible insider trading, escalate to human"
- **Impact**: Reduces analyst workload by 80%, allows focus on genuine risks

**2. Investigation Summary Generation**
- **Input**: 1,000 messages related to a case
- **AI Processing**: Summarizes timeline, key participants, risk indicators
- **Output**: 2-page executive summary for legal/compliance review
- **Impact**: Reduces case review time from days to hours

**3. Regulatory Report Drafting**
- **Input**: Flagged incident requiring SAR (Suspicious Activity Report) filing
- **AI Processing**: Drafts initial report based on captured evidence
- **Output**: Pre-filled SAR form for human review and submission
- **Impact**: Reduces report preparation time by 60%

**4. Policy Violation Prediction**
- **Training**: Historical policy violations and precursor behaviors
- **Prediction**: Flags employees exhibiting similar behavioral patterns
- **Use Case**: Proactive coaching before violation occurs

#### Partnership: OpenAI Integration
- Announced in 2025 roadmap
- Enhances capture and analysis capabilities
- LLM-powered contextual understanding across 80+ channels

---

## Data Enrichment & Contextualization

### HR System Integration
**Enriched Metadata**:
- Employee department, title, reporting structure
- Insider list membership
- Training completion status
- Previous policy violations

**Enhanced Query**:
"Show all communications about Project Titan, but ONLY from employees in Advisory department who are NOT on the Insider List and have NOT completed insider trading training"

**Risk Amplification**:
If an employee on the Insider List suddenly communicates about restricted information with someone NOT on the list, the risk score multiplies exponentially.

---

### Market Data Correlation

**External Data Sources**:
- Stock price movements
- Trading volumes
- Market events (earnings announcements, M&A news)

**Correlation Analysis**:
"Flag any communications containing 'merger' OR 'acquisition' that occurred within 72 hours BEFORE a target company's stock price moved >10%"

**Insider Trading Detection**:
Cross-reference employee trades (from brokerage data) with communications mentioning specific securities

---

## Machine Learning Model Types

### Supervised Learning Models
**Use Cases**:
- **Classification**: Email is compliant / non-compliant
- **Named Entity Recognition**: Extract company names, dates, monetary amounts
- **Sentiment Classification**: Positive / Negative / Neutral / Secretive

**Training**:
- Labeled datasets from historical compliance investigations
- Continuous retraining as new policy violations identified

### Unsupervised Learning Models
**Use Cases**:
- **Clustering**: Group similar communications to identify unknown risk patterns
- **Topic Modeling**: Discover emerging themes in communications (e.g., sudden spike in "crypto" discussions)

**Value**:
Identifies risks that weren't explicitly programmed or known in advance

### Reinforcement Learning (Emerging)
**Use Case**: Optimize false positive reduction
**Mechanism**: System learns from analyst feedback (alert marked as "Not a Risk")
**Continuous Improvement**: Models improve accuracy over time based on real-world outcomes

---

## AI/ML Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **False Positive Reduction** | 90-95% | vs. lexicon-based systems |
| **True Positive Detection** | >98% | Catch rate for known policy violations |
| **Processing Latency** | <5 minutes | Time from message capture to risk alert |
| **Model Accuracy** | >95% | Intent classification accuracy |
| **Alert Precision** | 20-30% | Percentage of alerts that are genuine risks (up from 2-5% with keywords) |

---

## Compliance-Focused AI: The "Noise Problem"

### The Mathematical Necessity of AI

**The Scaling Challenge**:
- Financial institution: 10,000 employees
- Average: 100 communications/day per employee
- Total: 1 million messages/day
- Keyword system: 5% flagged as potential violations = 50,000 alerts/day
- Human analysts: Cannot possibly review 50,000 alerts/day

**Traditional Solution** (Doesn't Scale):
- Hire more analysts
- Result: Still overwhelmed, increased costs

**Smarsh AI Solution** (Scales):
- AI reduces 50,000 alerts to 2,500 high-probability risks (95% reduction)
- 2,500 alerts ÷ 25 analysts = 100 alerts/analyst/day (manageable)
- Human analysts focus on genuine risks, not noise

### ROI Calculation

**Cost Without AI**:
- 250 analysts required (50,000 alerts ÷ 200 per analyst per day)
- $75K average salary + benefits = $100K fully loaded cost
- Total: $25 million/year in analyst costs
- Plus: High analyst burnout, turnover, missed risks

**Cost With Smarsh AI**:
- 25 analysts required (2,500 alerts ÷ 100 per analyst per day)
- Total: $2.5 million/year in analyst costs
- **Savings**: $22.5 million/year
- Plus: Better detection rates, lower burnout, higher job satisfaction

---

## Generative AI Risk Monitoring (Emerging)

### The New Risk Vector

**Challenge**:
Employees increasingly use ChatGPT, Claude, Copilot to:
- Write client emails
- Generate code
- Summarize documents
- Draft reports

**Compliance Risk**:
- Confidential information leaked to third-party AI providers
- Intellectual property exposed
- Client data privacy violations

### Smarsh's Approach

**Capture Layer**:
- Monitor browser activity to detect GenAI tool usage
- Capture prompts sent to ChatGPT, Claude, Copilot
- Archive AI responses received

**Analysis Layer**:
- Classify prompts: Benign vs. Potentially Sensitive
- Flag prompts containing: Client names, Deal codes, Internal project names, Confidential data
- Alert: "Employee X sent confidential Project Titan details to ChatGPT"

**Policy Enforcement**:
- Real-time blocking of sensitive data in prompts (future capability)
- Employee education: Flagged incidents trigger training

---

## Technical SE Demo Points

### Demo Flow: NLP in Action

**Setup**:
"Let me show you the difference between keyword search and our AI-powered intent analysis."

**Keyword Search Demo**:
1. Search archive for word "tip"
2. Results: 10,000 messages (most are "thanks for the tip on that restaurant")
3. Analyst overwhelmed, signal buried in noise

**Smarsh NLP Demo**:
1. AI filters results for "financial tip-giving context"
2. Results: 12 messages (all genuine front-running / insider tip risks)
3. Analyst can immediately investigate genuine violations

**Closing**:
"This 99.9% reduction in noise means your compliance team can focus on actual risk instead of drowning in false positives. That's the power of AI that understands intent, not just keywords."

---

## Competitive Advantage: AI/ML Moat

### Why Smarsh's AI is Defensible

**1. Proprietary Training Data**:
- 20+ years of financial services communications
- Billions of messages across all channels
- Labeled datasets from real compliance investigations
- Competitors starting from scratch

**2. Digital Reasoning Pedigree**:
- Used by intelligence agencies (NSA, etc.)
- Proven at detecting sophisticated concealment
- Not a "demo" AI—battle-tested in high-stakes environments

**3. Continuous Learning Loop**:
- Every customer investigation improves models
- Network effects: More customers → More data → Better models → More attractive to new customers

**4. Multi-Channel Context**:
- AI trained on email, chat, voice, video simultaneously
- Understands how bad actors shift between channels to evade detection
- Competitors typically strong in one channel, weak in others
