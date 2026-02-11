# Contributing to SLMEducatorTRAE

This document consolidates collaboration rules, coding standards, and guidelines for all contributors (human and AI agents) working on the SLMEducatorTRAE project.

**Last Updated**: February 2, 2026

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Directory Structure](#directory-structure)
3. [Code Quality Standards](#code-quality-standards)
4. [Testing Requirements](#testing-requirements)
5. [Git & Workflow](#git--workflow)
6. [Documentation Guidelines](#documentation-guidelines)
7. [Communication Standards](#communication-standards)

---

## Core Principles

### Zero-Tolerance Standards

- **Zero Dead Code**: Remove ALL unused code, legacy artifacts, commented blocks
- **Zero Temp Files**: Delete ALL development scripts, debug files, temporary artifacts after use
- **Zero Shortcuts**: No TODO comments, no "fix later" compromises
- **Zero Assumptions**: Verify everything; never assume schemas, APIs, or relationships

### Collaboration Mindset

- **Proactivity**: When fixing a bug, search the entire codebase for similar issues and fix them all
- **Ultra-Thoroughness**: 
  - Identify and resolve root causes, not symptoms
  - Think deeply about implications and edge cases
  - Consider related issues systematically
- **Verification**: All work MUST be tested before being considered complete
- **Evidence**: Provide evidence that fixes work (tests, screenshots, logs)

### Initiative

- Be direct and concise in communication
- Take initiative to solve related problems without being asked
- Never ask permission for obvious cleanup or improvements
- Create reusable tools in `tools-generic/` instead of one-off scripts

---

## Directory Structure

### Source Code Organization

```
src/
├── core/           # Business logic, algorithms, data models
│   ├── models/     # Data models
│   └── services/   # Business services
├── api/            # API routes and endpoints
└── web/            # Frontend HTML/JS
```

### Test Organization

**ALL tests must be in `tests/` directory** - never in `src/`.

```
tests/
├── unit/           # Fast, isolated tests (< 1ms each)
├── integration/    # Component interactions (< 100ms each)
├── e2e/            # End-to-end workflows
├── real_ai/        # Tests with actual AI providers
├── ui/             # UI/visual tests
└── fixtures/       # Test fixtures and mocks
```

### Documentation Structure

```
docs/
|-- README.md                    # This file
|-- FUNCTIONAL_REQUIREMENTS.md   # Feature documentation
|-- MIGRATION_GUIDE.md           # Migration instructions
|-- CONTRIBUTING.md              # This file
|-- api/                         # API documentation
`-- i18n/                        # Internationalization
```

### Implementation Documents

**All task-specific docs go in `implementation_documents/`:**

- Implementation plans
- Audit reports
- Investigation logs
- Temporary reproduction scripts
- Performance analysis

**Naming convention**: `implementation_documents/{feature}_{date}_{type}.md`

Example: `implementation_documents/gui_audit_20251216_findings.md`

---

## Code Quality Standards

### Clean Code Policy

- **Remove Old/Legacy Code**: Actively remove code no longer used
- **No Commented-Out Code**: Delete code; Git history preserves old versions
- **Type Hints**: All functions must have type hints
- **Docstrings**: All public functions and classes need Google-style docstrings

### Code Review Standards

- **Complexity**: Functions should not exceed 50 lines
- **Cyclomatic Complexity**: Keep < 10 per function
- **Pattern Consistency**: Replicate existing code patterns exactly
- **Dependencies**: Use the same libraries/frameworks as existing code

### Dependencies

- Update `requirements.txt` immediately if changes require new libraries
- Pin versions for production stability (e.g., `package==1.2.3`)
- Periodically run `pip check` and review security advisories

### UI Styling (PySide6/Qt)

**NO INLINE STYLES**: Never use `setStyleSheet()` on individual widgets. Use the ThemeManager instead.

```python
# ❌ BAD
widget.setStyleSheet("background: #1E293B; color: #F1F5F9;")

# ✅ GOOD
from ui.styles.theme import ThemeManager
widget.setStyleSheet(f"background: {ThemeManager.SURFACE}; color: {ThemeManager.TEXT_PRIMARY};")
```

---

## Testing Requirements

### Mandatory Testing

Always run tests that might be affected:

```bash
pytest tests/ -v --tb=short
```

**Coverage Requirement**: Maintain minimum 80% code coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

### Test Categories

| Type | Speed | Purpose |
|------|-------|---------|
| Unit | < 1ms | Fast, isolated, deterministic |
| Integration | < 100ms | Component interactions |
| E2E | Variable | Full workflows |
| Real AI | Variable | Actual API calls (costs tokens) |

### Testing Rules

- **Real Integration**: Use real services/APIs when specified; avoid mocks unless requested
- **Cleanup**: Delete test data, users, files created during testing
- **Complete Coverage**: Test happy paths AND edge cases, errors, boundary conditions
- **Fix Before Finishing**: Fix ALL issues and regressions before marking complete

### Verification Checklist

- [ ] All affected unit tests pass
- [ ] Integration tests pass
- [ ] Code coverage >= 80%
- [ ] No new linting errors (`flake8`, `pylint`)
- [ ] Type checking passes (`mypy`)
- [ ] Manual testing completed (if needed)
- [ ] Documentation updated

---

## Git & Workflow

### Commit Messages

Format:
```
[TYPE] Brief description (50 chars max)

Detailed explanation if needed (72 char line wrap)
- Bullet points for multiple changes
- Reference issue/PR numbers: Fixes #123
```

Types: `[FEAT]`, `[FIX]`, `[REFACTOR]`, `[TEST]`, `[DOCS]`, `[PERF]`, `[SECURITY]`

### File Naming

- **Tests**: `test_<feature>_<purpose>.py`
- **Temporary**: `check_*.py`, `patch_*.py`, `fix_*.py` (DELETE after use)
- **Documentation**: ALL_CAPS for spec documents
- **Artifacts**: lowercase with underscores

### What to Ignore

Already in `.gitignore`:
- `__pycache__/`, `*.pyc`
- `.env`, `env.properties`, `settings.properties`
- `logs/`, `*.log`
- `*.db`, `*.db-wal`, `*.db-shm`
- `.coverage`, `htmlcov/`
- Temporary scripts: `verify_*.py`, `inspect_*.py`, `reproduce_*.py`

### What to Delete

**DELETE after use:**
- Debugging scripts (`check_*.py`, `debug_*.py`, `inspect_*.py`)
- Temporary patches (`patch_*.py`, `fix_*.py`, `temp_*.py`)
- Development helpers (`add_*.py`, `update_*.py`, `export_*.py`)
- Empty log files

**KEEP:**
- Integration tests (`test_*_integration.py`)
- Unit tests for all features
- End-to-end test suites

---

## Documentation Guidelines

### Internationalization (i18n)

- **Proactive Translation**: Add translation keys to BOTH `en.json` and `es.json` for new UI
- **No Hardcoded Strings**: All user-facing text must use `data-i18n` attributes
- **Check All Languages**: Never leave a key missing in one language

### Docstring Template

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief one-line description.
    
    Extended description explaining the function's purpose, behavior,
    and any important details about how it works.
    
    Args:
        param1: Description of param1 and valid range/values.
        param2: Description of param2 and valid range/values.
    
    Returns:
        Description of return value and structure.
    
    Raises:
        ValueError: When param1 is invalid.
        RuntimeError: When operation fails due to external factor.
    
    Example:
        >>> result = function_name(value1, value2)
        >>> print(result)
        expected_output
    """
```

### Markdown Artifacts

For substantial work, create:

- `task.md`: Checklist breakdown before starting
- `implementation_plan.md`: Proposed changes grouped by component
- `walkthrough.md`: What was done and tested
- `ultra_deep_review.md`: Comprehensive reviews with gap analysis

**Formatting Rules:**
- Use markdown headers, bullets, code blocks
- Links: `[filename](file:///absolute/path)`
- Checkboxes: `[ ]` todo, `[/]` in-progress, `[x]` done

---

## Communication Standards

### Response Format

- **Conciseness**: Brief, direct communication; details go in artifacts
- **Structure**: Use markdown headers, bullets, code blocks
- **Summaries First**: Start with accomplishments, not process details
- **Evidence**: Include screenshots, terminal output, test results

### Handling Uncertainty

**Priority Order:**
1. **Investigate**: Check files, search code, inspect schemas
2. **Test Hypothesis**: Write small verification scripts
3. **Ask Specifically**: If blocked, ask targeted questions with context

**Never:**
- ❌ Make assumptions about data structures
- ❌ Guess at API contracts or schemas
- ❌ Assume relationships between entities
- ❌ Skip verification steps

### Ultra-Deep Reviews

When reviewing comprehensively:

- **Line-by-Line**: Compare EVERY requirement against implementation
- **Gap Analysis**: Document ALL missing features, bugs, inconsistencies
- **Relationships**: Check ALL foreign keys, references, dependencies
- **Coverage**: Provide X/Y completion tracking
- **Justification**: Document intentional deviations with rationale

### Browser Testing (Antigravity)

- **Single Tab Policy**: Maintain only 1 tab in browser
- **Close Tabs After**: Close all extra tabs before returning
- **60 Second Limit**: Force-close operations after 60 seconds if stuck

---

## Task Completion Criteria

A task is complete when ALL of the following are satisfied:

✅ **Code Quality**
- Type hints present and correct
- Docstrings complete
- No dead code or commented-out code
- Linting passes

✅ **Testing**
- All existing tests pass
- New tests written for new functionality
- Edge cases tested
- Code coverage >= 80%

✅ **Documentation**
- Implementation document created if substantial
- Complex logic documented
- API changes documented

✅ **Git & Cleanup**
- Temporary files removed
- No secrets or debug artifacts committed
- Commit messages clear and descriptive

---

## Resources

- **Test Users**: See `TEST_USERS.txt`
- **Environment variables**: Copy `.env.example` to `.env`
- **App config**: Copy `env.properties.example` to `env.properties`
- **API Docs**: See `docs/api/`

---

**Remember**: Surface-level solutions are unacceptable. Every task deserves comprehensive analysis, thorough execution, and complete verification.
