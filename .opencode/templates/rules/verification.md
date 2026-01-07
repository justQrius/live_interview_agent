---
paths: tests/**/*
---
# Verification Rules

## Test Pyramid Targets

- Unit tests: ~60%
- Integration tests: ~30%
- E2E tests: ~10%

## Cross-Platform Testing

If multi-platform support required:
- Run tests across OS matrix (Windows/Linux/macOS)
- Test with target runtime versions
- Automate in CI/CD

## Integration Test Checklist

For each integration:
- [ ] Happy path
- [ ] Error cases
- [ ] Timeouts
- [ ] Retries and circuit breakers
- [ ] Concurrency scenarios
- [ ] Cleanup and rollback
- [ ] Platform variations

## Security Testing

- [ ] SAST scan completed
- [ ] Dependency vulnerability scan clean
- [ ] Secrets scanning passed
- [ ] DAST against staging (if applicable)

## Performance Testing

- [ ] Benchmarks for critical paths (p95/p99)
- [ ] Regression tracking against baseline
- [ ] Load tests in staging (for services)

## Documentation

Before marking Done:
- [ ] README updated
- [ ] API documentation current
- [ ] Runbook updated (if operational)
- [ ] ADRs updated (if decisions changed)

## Gate Checklist

Before marking Done:
- [ ] Coverage target met
- [ ] CI green across all platforms
- [ ] Security scans clean
- [ ] Documentation updated
- [ ] Parallel reviews completed

## Reference

See `docs/SDLC_BEST_PRACTICES.md` for complete guidelines.
