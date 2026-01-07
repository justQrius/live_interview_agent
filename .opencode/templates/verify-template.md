# Verification Checklist

**Story/Feature:** [Name]  
**Date:** YYYY-MM-DD  
**Verifier:** [Agent/Person]

---

## Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] E2E tests for critical paths
- [ ] Coverage target met (Target: ___%)

**Actual Coverage:** ____%

---

## CI/CD Validation

- [ ] CI pipeline green
- [ ] All platforms tested (Windows/Linux/macOS)
- [ ] Build artifacts generated successfully
- [ ] No new warnings/deprecations

**CI Run Link:** [Link]

---

## Security Review

- [ ] SAST scan completed
- [ ] Dependency vulnerability scan clean
- [ ] Secrets scanning passed
- [ ] No hardcoded credentials
- [ ] Input validation verified
- [ ] AuthN/AuthZ checked

**Security Notes:**


---

## Performance Review

- [ ] No performance regression detected
- [ ] Critical path latency within target
- [ ] Load testing completed (if applicable)
- [ ] Memory usage acceptable

**Performance Notes:**


---

## Code Quality

- [ ] Code review completed
- [ ] Linting passed
- [ ] No code smells flagged
- [ ] Design patterns followed
- [ ] Error handling comprehensive

**Reviewers:**


---

## Documentation

- [ ] README updated (if applicable)
- [ ] API documentation updated
- [ ] Code comments added for complex logic
- [ ] ADRs updated (if decisions changed)
- [ ] Runbook updated (if operational changes)

---

## Parallel Review Aspects

| Aspect | Reviewer | Status | Notes |
|--------|----------|--------|-------|
| Quality | | ☐ Pending / ✅ Pass / ❌ Fail | |
| Security | | ☐ Pending / ✅ Pass / ❌ Fail | |
| Performance | | ☐ Pending / ✅ Pass / ❌ Fail | |

---

## Outstanding Items

| Item | Priority | Owner | Due |
|------|----------|-------|-----|
| | | | |

---

## Sign-off

- [ ] All checklist items complete or explicitly deferred
- [ ] Outstanding items tracked in beads
- [ ] Ready for deployment

**Verified By:** ________________  
**Date:** ________________
