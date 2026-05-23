# Code Manifesto Memo

## Context
**These are personal tools, not enterprise software.**

This manifesto governs scripts and tools I write for myself. No other users. No team. No customers. Just me, solving my own problems, in my own way.

## Core Philosophy
**Write code so simple that you can understand it three months from now at 3 AM.**

Since I'm the only user, I can be opinionated, direct, and unapologetic about design choices. No committees, no consensus, no compromise.

## The Commandments

### 1. Minimalism Above All
- Every line of code is a liability
- If you can solve it in 10 lines, don't write 100
- Delete code ruthlessly - the best code is no code
- Resist the urge to add "just in case" features

### 2. One Tool, One Purpose
- Each script does ONE thing well
- Clone and specialize rather than generalize
- A tool that does everything does nothing well
- Separation of concerns is sacred

### 3. Fail Fast, Fail Loud
- Errors should stop execution immediately
- No silent failures, ever
- If something is wrong, crash with a clear message
- Don't try to be smart about recovery

### 4. Sequential by Default
- Concurrent processing is the exception, not the rule
- Deterministic behavior > theoretical performance
- If you must parallelize, have a damn good reason
- Natural sorting (natsort) for all file operations

### 5. File System Respect
- Never move user files without explicit permission
- Never auto-archive or auto-organize
- Input files stay where they are
- Outputs go to timestamped directories (YYMMDD_HHMMSS)

### 6. Configuration Through Profiles
- YAML profiles for configuration
- Profiles live in designated directories
- Active profiles = active behavior
- No hardcoded magic values

### 7. Matrix Processing Pattern
- All inputs × All profiles = Total operations
- Process systematically and predictably
- Track success/failure comprehensively
- Generate reports automatically

### 8. Error Handling Hierarchy
```python
# Good
if not api_key:
    logger.error("No API key found")
    sys.exit(1)

# Bad
if not api_key:
    api_key = "default_key"  # NO! Never assume
```

### 9. Directory Structure Discipline
```
PROJECT/
├── src/           # Core logic only
├── USER-FILES/    # Sacred user space - DO NOT TOUCH
│   ├── 03.*/      # Configuration
│   ├── 04.*/      # Inputs (READ ONLY)
│   └── 05.*/      # Outputs (WRITE ONLY)
└── *.md           # Documentation (when requested)
```

### 10. Git Discipline
- Test before committing
- Never commit without running lint/typecheck
- Commit messages describe WHY, not WHAT
- No commits unless explicitly requested

### 11. Dependencies and Imports
- Use pathlib.Path, never os.path
- Type hints for all function signatures
- Requirements.txt with exact versions
- Virtual environments always

### 12. Logging and Output
- Use loguru for structured logging
- Rich for progress displays
- Clear, actionable error messages
- Cost reporting for expensive operations

### 13. The Anti-Patterns (Never Do These)
- **Clever code** - Be obvious, not clever
- **Premature optimization** - Make it work, then maybe make it fast
- **Assumption-based defaults** - Fail if missing, don't guess
- **Magic behavior** - Explicit > Implicit
- **Feature creep** - Resist the urge to "improve"

### 14. Documentation Philosophy
- Code should be self-documenting
- Comments explain WHY, not WHAT
- Create docs only when explicitly requested
- No README files unless asked
- No need for extensive docs - I know what my tools do

### 15. Testing Reality
- Test with real data in real scenarios
- One test file/image to start
- Expand testing only after basic success
- Cost estimation before large batches

### 16. Running
- The script should run with the command `python3 -m src.main`

## The Prime Directive

**When in doubt, choose the simpler solution.**

If you're choosing between two approaches and both work, pick the one that:
- Has fewer lines of code
- Has fewer dependencies
- Is easier to explain
- Would be easier to debug at 3 AM

## Implementation Patterns

### Input Discovery Pattern
```python
from natsort import natsorted

files = natsorted(directory.glob("*.txt"))
if not files:
    raise FileNotFoundError(f"No files found in {directory}")
```

### Process and Report Pattern
```python
results = process_matrix(inputs, profiles)
create_success_report(results)
create_cost_report(results)
logger.success(f"Completed: {results['success']}/{results['total']}")
```

### Validation Pattern
```python
# Check everything upfront
if not condition1:
    logger.error("Specific problem")
    sys.exit(1)
    
if not condition2:
    logger.error("Other specific problem")
    sys.exit(1)

# Only then proceed
process()
```

## The Mental Model

Think of code as a pipeline:
1. **Validate** - Check all preconditions
2. **Discover** - Find all inputs systematically  
3. **Process** - Transform inputs deterministically
4. **Report** - Document what happened
5. **Exit** - Clean termination

## Final Wisdom

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

This applies to code more than anything else. Every time you're about to add a feature, ask yourself:
- Do I explicitly need this?
- Can I solve the problem without this?
- Will this make the code harder to understand?

If any answer is yes, don't add it.

## Remember

These are my personal tools. I'm not writing code to impress anyone, accommodate other users, or follow "best practices" for team environments. I'm writing code to solve MY specific problems in the most straightforward way possible.

The best code is boring code - it does exactly what I expect, nothing more, nothing less. No edge cases for users that don't exist. No flexibility for use cases I don't have.

**Make it work. Keep it simple. Move on.**

---

*This manifesto is itself an example: direct, clear, no fluff. This is the way.*