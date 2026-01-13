# Smarsh Regulatory & Compliance Context

## The RegTech Market: 2025 Enforcement Landscape

### SEC & FINRA Priorities (2025)

**FINRA Annual Regulatory Oversight Report Highlights**:
1. **Off-Channel Communications**: Top priority
2. **Artificial Intelligence**: Emerging surveillance focus
3. **Third-Party Risk Management**: First-ever dedicated section in 2025 report
4. **AML, Fraud, and Sanctions Compliance**: Heightened scrutiny
5. **Regulation Best Interest (Reg BI)**: Continued focus on suitability

**SEC Enforcement Actions**:
- **2025**: Twelve firms fined $63+ million combined for recordkeeping failures
- **Q1 2025**: 200+ FINRA enforcement actions
- **Trend**: Billions in cumulative fines since 2021 for unmonitored messaging on personal devices
- **Focus**: WhatsApp, Signal, SMS usage by financial professionals

---

## Detailed 2025-2026 Regulatory Priorities

### Priority 1: Anti-Money Laundering (AML), Fraud, and Sanctions Compliance

**FINRA Identified Deficiencies**:
- **Customer Identification Programs (CIP)**: Failures to classify relationships as customer relationships, leading to inadequate identity verification
- **Customer Due Diligence (CDD)**: Insufficient suspicious activity identification
- **Suspicious Activity Reporting (SAR)**: Delays or failures in SAR filing

**Recent Enforcement Example**:
- **June 2025**: Expansion of U.S. sanctions designations against cryptocurrency shadow banking networks
- **Response Requirement**: Financial institutions required to adjust systems within 72 hours
- **Implication**: Demonstrates surgical precision and speed of modern regulatory response

**Smarsh Value Proposition**: Real-time monitoring across 100+ channels enables rapid detection of suspicious patterns and sanctions compliance violations

---

### Priority 2: Artificial Intelligence Governance

**SEC Requirements**:
- Firms must have adequate AI policies and procedures for:
  - Fraud prevention
  - Back-office operations
  - AML compliance
  - Trading functions

**2025 GAO Report - Key Finding**:
> "Insufficient explainability in AI models can inhibit a financial institution's understanding of a model's conceptual soundness and reliability, inhibit independent review and audit, and make compliance with laws and regulations more difficult."

**Competitive Advantage for Smarsh**:
- Domain-trained, transparent AI models vs. black-box systems
- Explainable AI for regulatory scrutiny
- Audit trails showing how AI reached conclusions
- Human-in-the-loop capabilities for high-stakes decisions

**Customer Pain Point Addressed**:
Firms using ChatGPT, Claude, or other general-purpose LLMs for compliance risk regulatory pushback due to lack of explainability. Smarsh's purpose-built compliance AI with transparent decision-making addresses this requirement.

---

### Priority 3: Third-Party Risk Management

**FINRA 2025 Innovation**:
First-ever dedicated section on third-party risk landscape in FINRA Annual Regulatory Oversight Report

**Firm Requirements**:
1. **Supervisory Systems**: Establish and maintain systems and written procedures ensuring compliance when using third-party services
2. **Due Diligence**: Conduct thorough vendor assessments before engagement
3. **Data Protection Validation**: Validate data protection controls in vendor contracts
4. **Comprehensive Vendor Lists**: Maintain lists of all third-party services used

**Smarsh Positioning**:
- As customers evaluate Smarsh, they're conducting third-party risk assessments
- Smarsh must demonstrate: SOC 2 Type II compliance, data encryption standards, access controls, incident response procedures
- AWS partnership provides additional validation (AWS itself is heavily audited by regulators)

---

### Priority 4: Investment Adviser Compliance - New TAM Opportunity

**Major Regulatory Change**:
**Effective Date**: January 1, 2026
**Change**: SEC-registered investment advisers (RIAs) and exempt reporting advisers (ERAs) now classified as "financial institutions" under Bank Secrecy Act

**New Requirements for RIAs/ERAs**:
- Full AML/CFT (Anti-Money Laundering / Countering Financing of Terrorism) programs
- SAR (Suspicious Activity Report) filing obligations
- Travel Rule compliance
- Enhanced customer due diligence

**Penalties**:
Up to $5,000 per violation (can accumulate rapidly)

**Implication for Smarsh**:
- **TAM Expansion**: Entire RIA market segment (thousands of firms) now requires compliance infrastructure
- **Urgency**: Firms have until January 1, 2026 to implement programs
- **Opportunity**: RIAs historically underserved by compliance tech vendors; greenfield opportunity

**Sales Positioning**:
"As of January 1, 2026, your firm is classified as a financial institution under the Bank Secrecy Act. That means you need the same AML compliance infrastructure as banks—including communications monitoring. Smarsh helps RIAs achieve compliance without building from scratch."

---

### Priority 5: Regulation Best Interest (Reg BI) and Form CRS

**Continued Deficiencies**:
- Failures to conduct reasonable investigations before recommending securities
- Inadequate suitability assessments
- Excessive or unsuitable recommendations

**Form CRS Requirements**:
- Accurate, timely disclosures about client relationships
- Amendments and filing requirements (delayed but ongoing)

**Smarsh Relevance**: Communications archive provides defensible evidence of suitability discussions and disclosures

---

### Regulatory Drivers for Smarsh Adoption

**Primary Motivation**: Survival against existential regulatory threats, not just efficiency

**Key Regulations**:
- **SEC Rule 17a-4**: Record retention requirements for broker-dealers
- **FINRA Rules**: Communications supervision and archiving
- **MiFID II**: European equivalent driving global harmonization
- **GDPR**: Data privacy requirements in Europe
- **CCPA**: California privacy law
- **HIPAA**: Healthcare communications compliance

---

## Off-Channel Communications Crisis

### The Regulatory Problem

**Definition**: "Off-channel" = Communications on unmonitored personal devices or applications

**Regulatory Stance**:
- Regulators (SEC, CFTC, FINRA) conducting "sweeps"
- Firms must prove they're monitoring employee text messaging and encrypted apps
- Failure to monitor = presumption of guilt in investigations

### Real-World Impact

**Fine Examples**:
- Major banks: $200M+ each for WhatsApp violations
- Combined industry fines: Billions since 2021
- Personal liability: CCOs and executives held accountable

**Smarsh Solution**:
- Capture Mobile technology for WhatsApp, Signal, Telegram, WeChat
- Defensible audit trail for dispersed workforce
- SEC 17a-4 compliant archiving

---

## SEC Rule 17a-4: Technical Requirements

### WORM Storage Mandate

**Write-Once-Read-Many (WORM)**:
- Records must be preserved in non-rewriteable, non-erasable format
- Retention periods: 3-7 years depending on record type
- Even system administrators cannot delete before retention expires

**Smarsh Implementation**:
- S3 Object Lock enforces WORM at infrastructure level
- Tamper-evident audit trails
- Third-party attestation of compliance

### Immutability Requirements

**What's Required**:
- Complete and accurate records
- Native format preservation where applicable
- Index for efficient retrieval
- Duplicate copy at separate location

**Why It Matters**:
- Courts require evidence in original context (emojis, threading, edits)
- Altered records = inadmissible evidence
- Missing records = adverse inference (jury assumes deleted content was incriminating)

---

## eDiscovery Trends

### Modern Evidence Formats

**Evolution of Evidence**:
- **2005**: Email printouts sufficient
- **2025**: Courts demand:
  - Emoji context
  - Edit history
  - Thread relationships
  - Reaction timestamps
  - GIF/meme content

**Example Case**:
Trader sends: "Let's discuss offline 🤫"
- Legacy system: Captures text only
- Smarsh: Captures "shushing face" emoji context
- Legal impact: Emoji proves intent to conceal

### Volume Challenge

**Data Explosion**:
- Average employee: 100+ communications/day
- Enterprise (10K employees): 1M messages/day
- Annual: 365M messages
- 5-year retention: 1.8 billion messages

**Traditional eDiscovery Problem**:
- Export everything to external review platform: $2-5 per document
- 10M documents in case = $20-50M in review costs

**Smarsh Solution**:
- In-house culling reduces dataset 99% before export
- AI identifies relevant documents
- Export only 10K instead of 10M
- Cost: $20K instead of $20M

---

## Financial Services Compliance Trends

### The "Noise Problem"

**Mathematical Challenge**:
- Keyword systems flag 5% of messages as potential violations
- 1M messages/day × 5% = 50,000 alerts/day
- Human analysts cannot review 50,000 alerts/day
- Result: Overwhelmed teams, missed risks, high burnout

**AI Imperative**:
- Not optional—mathematical necessity
- Smarsh AI reduces 50,000 to 2,500 high-probability alerts (95% reduction)
- Human analysts can now focus on genuine risks

### False Positive Economics

**Cost Without AI**:
- 250 analysts needed (50K alerts ÷ 200/analyst/day)
- $100K fully loaded cost per analyst
- Total: $25M/year in compliance labor costs
- Plus: Burnout, turnover, missed violations

**Cost With Smarsh AI**:
- 25 analysts needed (2.5K alerts ÷ 100/analyst/day)
- Total: $2.5M/year
- **Savings**: $22.5M/year

---

## Cloud Adoption in Regulated Industries

### Security Paradigm Shift

**Historical View** (2010-2020):
- Cloud = insecure
- Must keep data on-premises for security

**Current View** (2025):
- Cloud providers (AWS, Azure, GCP) have BETTER security than typical enterprise data center
- Compliance certifications: SOC 2, ISO 27001, FedRAMP
- Shared responsibility model well understood

### Drivers for Cloud Migration

**1. Compute Power for AI**:
- Advanced AI requires GPU clusters unavailable on-premises
- AWS SageMaker, Bedrock enable sophisticated ML
- On-prem systems cannot match cloud AI capabilities

**2. Scalability**:
- Modern multimedia data (video calls, voice) generates 10x data vs. legacy email
- On-prem systems cannot scale economically
- Cloud provides elastic capacity

**3. Business Continuity**:
- Cloud providers offer 99.99% uptime SLAs
- Multi-region redundancy
- On-prem disaster recovery expensive and unreliable

---

## Data Sovereignty & Residency

### Global Regulatory Patchwork

**Regional Requirements**:
- **GDPR (Europe)**: Personal data of EU citizens must stay in EU
- **CCPA (California)**: Similar requirements for California residents
- **China**: Data about Chinese operations must stay in China
- **Russia**: Data localization laws
- **Switzerland**: Banking secrecy laws

### Smarsh Multi-Region Strategy

**AWS Global Infrastructure**:
- 32+ regions worldwide
- Smarsh can deploy archive in specific geographies
- German data in Frankfurt, UK data in London, etc.

**No CapEx Required**:
- Traditional approach: Build physical data centers in each country ($$$)
- Smarsh approach: Leverage AWS existing infrastructure
- Spin up new regions as needed

---

## Industry-Specific Compliance

### Financial Services

**Regulations**:
- SEC Rule 17a-4, FINRA 4511, MiFID II, EMIR
- Focus: Market manipulation, insider trading, front-running

**Smarsh Strengths**:
- 20+ years in financial services
- Deep integration with financial platforms (Bloomberg, Symphony, ICE)
- Understands trader terminology and behaviors

### Public Sector / Government

**Regulations**:
- FOIA (Freedom of Information Act)
- Sunshine Laws
- Records retention mandates

**Use Cases**:
- Responding to public records requests
- Preserving government employee communications
- Transparency requirements

### Healthcare

**Regulations**:
- HIPAA (patient privacy)
- Patient communication standards

**Use Cases**:
- Doctor-patient messaging compliance
- Protected Health Information (PHI) archiving

### Energy & Utilities

**Regulations**:
- Trading communications (similar to financial services)
- NERC CIP (Critical Infrastructure Protection)

**Use Cases**:
- Energy trading desk supervision
- Grid operations communications

---

## Insider Trading Detection

### Regulatory Expectation

**What Regulators Want**:
- Proactive monitoring, not reactive investigation
- Firms must demonstrate they have systems to detect insider trading BEFORE regulators discover it

### Smarsh Capabilities

**Multi-Source Correlation**:
1. **Communications**: Capture all channels (email, chat, voice, mobile)
2. **Trading Data**: Integrate with brokerage systems
3. **Market Data**: Stock prices, volumes, events
4. **HR Data**: Insider lists, employee roles

**Detection Scenario**:
- Employee mentions "Project Titan" in WhatsApp
- Cross-reference: Employee NOT on Project Titan insider list
- Cross-reference: Employee or family member traded related stock within 48 hours
- Cross-reference: Stock price moved >10% following trade
- **Alert**: High-probability insider trading, escalate to legal

---

## Market Manipulation Detection

### Regulatory Focus

**Types**:
- **Spoofing**: Placing fake orders to manipulate price
- **Front-Running**: Trading ahead of client orders
- **Pump and Dump**: Inflating stock price then selling

### Detection Methods

**Behavioral Patterns**:
- Sudden surge in communications about specific security
- Coordination between traders ("Let's both buy at 2 PM")
- Celebratory messages after price moves ("We made a killing on XYZ today")

**NLP Advantage**:
- Understands euphemisms and coded language
- Detects sentiment shift (casual → urgent → celebratory)
- Maps communication networks to identify collusion

---

## Harassment & Toxic Culture Monitoring

### Expanding Compliance Scope

**Beyond Financial Crime**:
- Regulators increasingly focused on workplace culture
- #MeToo movement impact
- Board-level accountability for toxic environments

**Corporate Risk**:
- Reputational damage
- Executive dismissals
- Shareholder lawsuits

### Smarsh Conduct Module

**Detection Capabilities**:
- Harassment language (sexual, discriminatory)
- Bullying and intimidation patterns
- Toxic management behaviors

**Privacy Balance**:
- Alert on policy violations, not personal content
- Human review before escalation
- Clear policies on monitoring scope

---

## Generative AI Compliance Risk

### Emerging Regulatory Concern

**The Problem**:
- Employees using ChatGPT, Claude, Copilot for work
- Inadvertently leaking:
  - Client names and deal details
  - Proprietary code and IP
  - Confidential financial data

**Regulatory View**:
- GenAI usage = new compliance blind spot
- Firms must monitor what employees share with AI tools

### Smarsh Roadmap

**Capture & Monitor**:
- Detect GenAI tool usage (browser activity, API calls)
- Capture prompts sent to ChatGPT, Claude, etc.
- Archive AI responses received

**Analysis & Alerting**:
- Classify prompts as Benign vs. Sensitive
- Flag prompts containing confidential information
- Policy enforcement: Block or alert on violations

---

## Regulatory Strategy: Smarsh as "Insurance"

### Value Proposition Framing

**Cost vs. Benefit**:
- **Smarsh Annual Cost**: $500K - $2M depending on scale
- **Single SEC Fine**: $10M - $200M
- **ROI Calculation**: One avoided fine pays for 10+ years of Smarsh

**Risk Transfer**:
"Smarsh isn't a cost center—it's insurance. You're transferring the risk of a catastrophic fine to a proven platform that's protected 18 of the top 20 banks for 20+ years."

### Board-Level Positioning

**CISO/CCO Presentation**:
- "The board has three options:"
  1. "Do nothing: Accept 100% of regulatory risk (not defensible)"
  2. "Build in-house: $10M+ investment, 2+ years, unproven (high risk)"
  3. "Deploy Smarsh: Proven solution, 90-day deployment, backed by AWS (low risk)"
