---
paths: _prism/planning/**/*
---
# Planning Phase Rules

## PRD Requirements

- PRD **must** include Non-Functional Requirements (NFRs) section
  - Latency/throughput targets (p95, p99)
  - Reliability SLOs
  - Security requirements
  - Observability expectations
  - Cost constraints

- Risk Matrix **required** for all integrations
  - Classify as HIGH/MEDIUM/LOW
  - HIGH-risk items require spike plans

- AI Usage Rules section recommended
  - What agents may generate
  - Validation requirements

## Gate Checklist

Before proceeding to Solutioning:
- [ ] PRD exists with NFRs
- [ ] Risk Matrix filled
- [ ] HIGH-risk items have spike plans
- [ ] Stakeholder approval obtained

## Reference

See `docs/SDLC_BEST_PRACTICES.md` for complete guidelines.
