# PRD: [Feature Name]

> **Status**: Draft | Under Review | Approved
> **Created**: [Date]
> **Author**: [Name/Agent]

---

## Problem Statement

[Clear description of the problem, including:]
- What user pain points exist
- What business impact this has
- Why current solutions are inadequate

---

## Goals

- [ ] [Measurable goal 1 with success metric]
- [ ] [Measurable goal 2 with success metric]
- [ ] [Measurable goal 3 with success metric]

## Non-Goals

> What we are explicitly NOT doing in this scope

- [Out of scope item 1]
- [Out of scope item 2]

---

## User Personas

### [Persona 1: Name/Role]

| Attribute | Description |
|-----------|-------------|
| **Who** | [Description of who they are] |
| **Needs** | [What they need from this feature] |
| **Pain Points** | [Current frustrations] |
| **Success Criteria** | [How we know we've helped them] |

### [Persona 2: Name/Role]

| Attribute | Description |
|-----------|-------------|
| **Who** | |
| **Needs** | |
| **Pain Points** | |
| **Success Criteria** | |

---

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | [Description] | Must Have | [Testable criterion] |
| FR-2 | [Description] | Must Have | [Testable criterion] |
| FR-3 | [Description] | Should Have | [Testable criterion] |
| FR-4 | [Description] | Could Have | [Testable criterion] |

> **Priority Legend**: Must Have (required for launch), Should Have (important but not blocking), Could Have (nice to have)

---

## Non-Functional Requirements (NFRs)

> Per SDLC Best Practices, always specify these at minimum.

| Category | Requirement | Target | Notes |
|----------|-------------|--------|-------|
| **Performance** | Response latency | p95 < ___ms, p99 < ___ms | Critical paths |
| **Performance** | Throughput | ___ req/sec | Under load |
| **Reliability** | Availability SLO | ___% uptime | Error budget |
| **Reliability** | MTTR target | < ___ minutes | Incident recovery |
| **Scalability** | Concurrent users | ___ users | Horizontal scaling? |
| **Security** | AuthN/AuthZ | [Standard] | OWASP Top 10 |
| **Security** | Data encryption | [At rest/In transit] | Compliance |
| **Observability** | Logging level | [Structured/Trace IDs] | OpenTelemetry? |
| **Observability** | Metrics | RED metrics | Rate/Error/Duration |
| **Cost** | Estimated cost | $___/month | Per environment |

---

## Risk Assessment Matrix

> Every HIGH-risk item must have an explicit mitigation and owner.

| Component/Integration | Risk Level | Reason | Mitigation Strategy | Owner |
|-----------------------|------------|--------|---------------------|-------|
| [External API X] | HIGH | Unknown reliability | Spike + circuit breaker | [Name] |
| [Async + DB] | HIGH | Event loop conflicts | Spike + executor isolation | [Name] |
| [Standard CRUD] | LOW | Known pattern | Framework patterns | [Name] |

---

## Spike Plan

> HIGH-risk integrations require technical validation before architecture.

| Integration | Risk | Spike Required | Time Budget | Owner | Status |
|-------------|------|----------------|-------------|-------|--------|
| [Tech A + Tech B] | HIGH | Yes | 2 hours | [Name] | ☐ Pending |
| [External Service] | MEDIUM | Optional | 1 hour | [Name] | ☐ Pending |

**Spike Template:** See `templates/spike-template.md`

---

## Use Cases

### UC-1: [Use Case Name]

**Actor**: [Who performs this action]
**Preconditions**: [What must be true before]
**Postconditions**: [What is true after]

**Flow**:
1. User does X
2. System responds with Y
3. User confirms Z

**Alternative Flows**:
- If [condition], then [action]

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| [Metric name] | [Baseline] | [Goal] | [When] |
| [Metric name] | [Baseline] | [Goal] | [When] |

---

## Dependencies

- **External**: [Third-party services, APIs]
- **Internal**: [Other teams, systems, features]
- **Technical**: [Libraries, infrastructure]

---

## AI Usage Rules

> How AI agents may assist with this feature.

| Aspect | Policy |
|--------|--------|
| **Code generation** | AI may generate boilerplate; humans own correctness |
| **Test generation** | AI may draft tests; humans verify assertions |
| **Documentation** | AI may draft; humans review accuracy |
| **Validation requirement** | All AI output must be tested, not just reviewed |

---

## Open Questions

- [ ] [Question 1 that needs answering]
- [ ] [Question 2 that needs answering]
- [ ] [Question 3 that needs answering]

---

## Gate Checklist (Planning → Solutioning)

Before proceeding to architecture:
- [ ] PRD reviewed and approved
- [ ] NFRs section complete
- [ ] Risk Matrix filled
- [ ] HIGH-risk items have spike plans
- [ ] Open questions resolved or deferred

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| [Term] | [Definition] |

### References

- [Link to related documents]
- [docs/SDLC_BEST_PRACTICES.md](../docs/SDLC_BEST_PRACTICES.md) - SDLC constitution
