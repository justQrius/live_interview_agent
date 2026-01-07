# Spike: [Technology A] + [Technology B] Integration

**Purpose:** Validate that [X] and [Y] work together on [platform]  
**Time Budget:** 1-2 hours  
**Date:** YYYY-MM-DD  
**Owner:** [Name]

---

## Hypothesis

[What we expect to work and why we're uncertain]

---

## Success Criteria

- [ ] [Specific testable outcome 1]
- [ ] [Specific testable outcome 2]
- [ ] [Performance target if applicable]

---

## Test Environment

| Platform | Version | Notes |
|----------|---------|-------|
| OS | | |
| Runtime | | |
| Dependencies | | |

---

## Test Code

```python
"""
Spike: [Technology A] + [Technology B] Integration
Purpose: Validate that X and Y work together on [platform]
Time Budget: 1-2 hours
Success Criteria: [Specific testable outcome]
"""

def test_integration():
    # Initialize components
    component_a = initialize_a()
    component_b = initialize_b()
    
    # Test interaction
    result = component_a.interact_with(component_b)
    
    # Validate outcome
    assert result == expected_outcome
    
    # Cleanup
    cleanup()

if __name__ == "__main__":
    test_integration()
    print("✅ Integration validated")
```

---

## Test Execution Log

### Run 1
**Date/Time:** 
**Platform:** 
**Result:** ✅ Pass / ❌ Fail

**Observations:**


### Run 2 (if needed)
**Date/Time:** 
**Platform:** 
**Result:** ✅ Pass / ❌ Fail

**Observations:**


---

## Findings

### What Worked

- 

### Issues Encountered

| Issue | Severity | Workaround |
|-------|----------|------------|
| | | |

### Performance Numbers (if applicable)

| Metric | Target | Actual |
|--------|--------|--------|
| | | |

---

## Decision

**Outcome:** ✅ GO / ❌ NO-GO / ⚠️ INVESTIGATE

### GO
- [ ] Proceed with integration
- [ ] Document any workarounds needed
- [ ] Update architecture with findings

### NO-GO
- [ ] Choose alternative approach
- [ ] Document why this failed
- [ ] Escalate to architecture review

### INVESTIGATE
- [ ] Need more time/resources
- [ ] Specific questions to answer:
  1. 
  2. 

---

## Next Steps

1. 
2. 
3. 

---

## Tenet Workflow (Hindsight Iteration)

> "For difficult features, let Claude write a 'throw-away first draft' end-to-end. 
> Analyze its errors and biases, then run a second, 'sharper' iteration informed 
> by what was learned from the first attempt."

This workflow is especially useful when:
- Integrating unfamiliar technologies
- Building complex features with unclear requirements
- Learning a new codebase or API

### Round 1: Discovery Draft

**Goal**: Learn by doing. Don't aim for production quality.

1. Let the agent implement end-to-end with minimal constraints
2. **Observe** the mistakes, assumptions, and biases
3. Document what the agent got wrong and why
4. Note unexpected complexities or API behaviors

**Output**: A working but imperfect draft + a list of lessons learned

### Round 2: Informed Implementation

**Goal**: Build properly with hindsight from Round 1

1. Start fresh (new context) with lessons from Round 1
2. Add constraints and guidance based on observed mistakes
3. Be more specific about edge cases discovered
4. Reference actual API behavior observed in Round 1

**Output**: Production-quality implementation

### When to Use Tenet Workflow

| Situation | Use Tenet? |
|-----------|-----------|
| Simple, well-documented API | No - direct implementation |
| Complex integration with poor docs | Yes |
| Unfamiliar language/framework | Yes |
| Critical performance requirements | Yes - measure in Round 1 |
| Tight deadline | Maybe - single informed attempt |

### Documenting Tenet Iterations

After Round 1, add a section here:

#### Round 1 Learnings

**What worked:**
- 

**What failed:**
- 

**Unexpected discoveries:**
- 

**Constraints for Round 2:**
- 

---

## References

- [Link to relevant docs]
- [Link to library/API documentation]
- [Link to similar implementations]

