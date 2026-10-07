# SLMEducator Documentation

This directory contains maintained guides and separately dated validation reports.
Historical reports describe only the source, environment and scope they record.

## Getting started and operations

- [Contributing](CONTRIBUTING.md): coding, testing and documentation guidelines
- [Functional requirements](FUNCTIONAL_REQUIREMENTS.md): current teacher and student capabilities
- [Migration guide](MIGRATION_GUIDE.md): copy-first upgrade and key-preservation checklist
- [Portability and recovery](PORTABILITY_RECOVERY.md): maintained encrypted backup, create-only restore and schema upgrade procedure
- [Windows installer](WINDOWS_INSTALLER.md): packaging boundaries and native acceptance requirements

## Testing

Run `run_tests.bat --help` from the repository root for modes and options. Test
setup explicitly installs development dependencies. Synthetic modes disable real
providers; `--real-ai` requires confirmation or the explicit `--yes` opt-in and
may incur provider cost. Browser and native Windows checks remain separate gates.

- [Browser test guide](BROWSER_TEST.md): browser journeys and reporting
- [Frontend build and checks](../src/frontend/README.md): locked dependencies, typecheck, lint, DOM tests and canonical production build

## Current UI references

- [React appearance system](api/THEME_SYSTEM.md): shared provider, CSS tokens and accessibility boundaries
- [Appearance hook reference](api/API_THEME_MANAGER.md): maintained React API (the filename preserves existing documentation links)
- [Translation guide](i18n/TRANSLATION_GUIDE.md): English/Spanish React catalogs and contribution examples
- [Localization boundaries](i18n/TRANSLATION_IMPLEMENTATION_SUMMARY.md): React, Python service and native launcher responsibilities
- [Frontend contribution contracts](../src/frontend/CONTRACTS.md): shared primitives, API adapters and feature integration

## Project overview

SLMEducator combines teacher content creation, student management and assessment
review with student learning sessions, tutoring and progress tracking. FastAPI,
SQLAlchemy and SQLite provide the backend; the active learning interface is a
built React/TypeScript application. The Windows launcher uses Tkinter. Retired
Qt and legacy web modules are not current implementation references.
