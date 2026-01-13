# Technical & Executive Communication Scenarios

---

## 6. Explaining a Complex System to a Non-Technical Executive (CFO / CCO)

### Interviewer Intent (Why This Matters at Smarsh)

This is a translation test.

Dominic is not evaluating whether you can simplify technology — he already assumes that. He is testing whether you understand *what executives actually care about* in regulated environments:
- Financial risk
- Regulatory exposure
- Operational cost
- Personal accountability

### Core Framing (Open Like This)

"When I speak with executives, I avoid architecture diagrams and start with risk, cost, and control."

That sentence immediately signals executive presence.

### Canonical Answer (Cloud Archiving Example)

"If I were explaining cloud archiving to a CFO or Chief Compliance Officer, I'd frame it like this:

'Today, your communications data is a liability — it creates regulatory exposure, legal cost, and operational drag if it's fragmented or hard to search. Cloud archiving turns that liability into a controlled asset.

Instead of data being scattered across email servers, chat tools, and devices, everything is captured automatically, stored immutably, and made searchable in one place. That reduces regulatory risk, shortens investigations, and lowers outside counsel spend.

From a cost perspective, it replaces unpredictable legal and compliance costs with a predictable operating expense — while scaling automatically as communication volumes grow.'

If needed, I'll then map that value back to how the system works — but only after alignment on why it matters."

### Why This Works for Smarsh

This explanation aligns directly with how Smarsh is bought:
- Risk mitigation over feature depth
- Predictable cost over reactive fines
- Control and defensibility over storage

It avoids jargon while preserving credibility.

### 30-Second Version

"I explain complex systems to executives by framing them in terms of risk, cost, and control. For cloud archiving, it's about reducing regulatory exposure, speeding investigations, and turning unpredictable legal cost into predictable operations."

### If Dominic Pushes: 'What If They Ask for Technical Proof?'

"That's when I bring in the technical team or go deeper myself — but only after we agree on success metrics. Executives don't want more detail; they want fewer surprises."

### Mistakes You Avoid

- Leading with diagrams
- Overusing compliance acronyms
- Treating executives like engineers

---

## 8. Smarsh-Specific Technical Scenario: Archiving Zoom Meetings Without Killing Network Bandwidth

### Interviewer Intent (Why This Question Is Asked)

This scenario tests architectural judgment.

Dominic is looking for whether you:
- Think in systems and trade-offs
- Understand cloud-native patterns
- Can calm technical fear without hand-waving

### Core Framing (Set the Tone)

"When customers worry about bandwidth, it usually means they're picturing the wrong data flow."

That line positions you as a guide, not a debater.

### Canonical Answer (Enterprise-Grade)

"I'd start by clarifying that modern Zoom archiving doesn't require video files to traverse the corporate network.

The preferred approach is cloud-to-cloud capture, where Zoom recordings are transferred directly from Zoom's cloud into the Smarsh platform via secure APIs. That completely bypasses the customer's internal network, eliminating bandwidth impact.

If the concern is storage or cost rather than bandwidth, we can also scope selectively — archiving only regulated users, specific meeting types, or only recordings rather than live streams.

For customers with stricter requirements or hybrid setups, there are additional options like dedicated network paths or region-specific ingestion, but the key is that bandwidth impact is an architectural choice, not an inevitability.

The goal is to design capture in a way that's compliant, scalable, and invisible to end users."

### Why This Works for Smarsh

This answer reinforces:
- API-first, cloud-native ingestion
- Scalability without customer infrastructure pain
- Calm, confident handling of technical objections

It directly aligns with Smarsh's capture strategy for collaboration platforms.

### 30-Second Version

"Zoom archiving doesn't need to touch the customer's network. Using cloud-to-cloud capture, recordings move directly from Zoom into Smarsh securely. Bandwidth concerns are usually solved by choosing the right architecture."

### If Dominic Pushes: 'What About Edge Cases?'

"That's where we scope carefully — regulated users only, recording types, or hybrid models — and validate impact during a PoC. The architecture adapts to the constraint."

### Mistakes You Avoid

- Suggesting agents on end-user machines
- Overengineering before discovery
- Treating bandwidth fear as ignorance

---

## 9. Smarsh-Specific Technical Scenario: Migrating ~50TB of Data from Global Relay

### Interviewer Intent (Why This Is High-Signal)

This question tests whether you understand **compliance migrations as legal events**, not data-copy exercises.

Dominic is listening for:
- Respect for chain of custody and audit defensibility
- Comfort discussing cost, risk, and trade-offs
- Ability to lead customers through uncomfortable but necessary conversations

### Core Framing (Set the Stakes)

"A compliance archive migration isn't just about moving data — it's about preserving trust in the data."

That line immediately anchors you in the right mindset.

### Canonical Answer (Enterprise-Grade)

"I'd start by acknowledging two realities upfront: large legacy exports are expensive, and regulators care more about data integrity than speed.

The first step is scoping. We clarify what must be migrated — date ranges, content types, regulated users — so we're not blindly exporting everything. That often reduces volume significantly.

Next is format and validation. Smarsh ingestion tooling is designed to handle standard compliance formats like EML or PST, and we validate records during ingestion to ensure completeness and fidelity.

Most importantly, we maintain a clear chain of custody. Every stage — export, transfer, ingestion, and verification — is documented so auditors can see exactly where the data was and how it was handled.

I also set expectations early: this is a controlled, auditable process, not a weekend cutover. The outcome is a defensible archive that compliance teams can stand behind, not just data that 'made it across.'"

### Why This Works for Smarsh

This answer reinforces:
- Compliance-first migration philosophy
- Audit readiness over speed theater
- Honest handling of export fees and constraints

It aligns with how Smarsh wins against legacy incumbents.

### 30-Second Version

"Migrating from Global Relay is about preserving chain of custody, not just moving data. We scope carefully, ingest standard formats, validate records, and document every step so auditors can trust the result."

### If Dominic Pushes: 'What About Cost Objections?'

"I frame export cost as a one-time transition expense versus the ongoing cost and risk of staying put. Most compliance teams understand that trade-off once it's framed in regulatory terms."

### Mistakes You Avoid

- Minimizing export fees
- Treating migration as purely technical
- Promising unrealistic timelines

---

**Status:** Complete technical scenarios with executive communication and Smarsh-specific architectures
