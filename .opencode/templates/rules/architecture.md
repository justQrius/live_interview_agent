---
paths: _prism/architecture/**/*
---
# Architecture Phase Rules

## Mandatory Sections

Architecture documents **must** include:

- **ADR List**: Link to all ADRs for this architecture
- **Threat Model**: Entry points, assets, trust boundaries
- **Integration Boundaries**: Adapters/interfaces for external deps
- **Observability Plan**: Logging, metrics, tracing strategy

## Conditional Sections

Include when applicable:

- **Concurrency Model**: If async/threading/multiprocessing used
  - Threading model and blocking work strategy
  - Shared state and locking approach
  - Resource limits (thread pools, connection pools)

## ADR Requirements

For major decisions, create ADR with:
- Context and constraints
- Decision and commitment
- Alternatives considered
- Consequences (positive/negative)
- Validation status (spike completed?)

## Gate Checklist

Before proceeding to Implementation:
- [ ] Architecture document complete
- [ ] ADRs created for major decisions
- [ ] All spikes completed with GO/NO-GO
- [ ] Observability plan documented
- [ ] Threat model reviewed (if security-relevant)

## Reference

See `docs/SDLC_BEST_PRACTICES.md` for complete guidelines.
