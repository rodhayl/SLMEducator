# SLMEducator Documentation

This directory contains tracked project documentation and reference guides.

## Quick Navigation

### Getting Started
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Collaboration rules, coding standards, and contribution guidelines
- **[FUNCTIONAL_REQUIREMENTS.md](FUNCTIONAL_REQUIREMENTS.md)** - Feature documentation (teacher and student capabilities)
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Encryption key and JWT migration instructions

### Testing
- Run test suites from repository root with `run_tests.bat`.
- Use `run_tests.bat --help` to view available test modes and options.
- **[BROWSER_TEST.md](BROWSER_TEST.md)** - End-to-end browser test guide for Chrome DevTools workflows and reporting.

### API and Technical Reference
- **[api/THEME_SYSTEM.md](api/THEME_SYSTEM.md)** - Theme system documentation
- **[api/API_THEME_MANAGER.md](api/API_THEME_MANAGER.md)** - Theme manager API reference

### Internationalization
- **[i18n/TRANSLATION_GUIDE.md](i18n/TRANSLATION_GUIDE.md)** - Translation guidelines
- **[i18n/TRANSLATION_IMPLEMENTATION_SUMMARY.md](i18n/TRANSLATION_IMPLEMENTATION_SUMMARY.md)** - i18n implementation details

## Project Overview

SLMEducator is an AI-assisted educational platform with:
- Teacher features: content creation, student management, assessments, grading
- Student features: learning sessions, AI tutoring, progress tracking
- Technical stack: Python FastAPI, SQLite, SQLAlchemy, HTML/JavaScript frontend

## Directory Structure

```text
docs/
|-- README.md
|-- BROWSER_TEST.md
|-- CONTRIBUTING.md
|-- FUNCTIONAL_REQUIREMENTS.md
|-- MIGRATION_GUIDE.md
|-- api/
`-- i18n/
```
