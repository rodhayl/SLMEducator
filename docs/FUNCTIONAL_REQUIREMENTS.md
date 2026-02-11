# SLMEducator Functional Requirements and Capabilities

This document enumerates all user-facing and system functionality of SLMEducator from both Teacher and Student perspectives, and details how features are provided across UI, services, and AI/LLM configuration.

## Overview
- Role-based UX: distinct Teacher and Student dashboards and tabs (`ui/screens/**`).
- Rich AI-assisted workflows for planning, content creation, tutoring, and assessment (`database/services/ai_*`, `ui/components/*ai*`).
- Centralized configuration with environment-driven settings (`config/settings.py`).
- Robust testing across unit, integration, UI, and E2E, including real-provider AI tests (`tests/**`).

## Teacher Functionality
- Dashboard and Navigation
  - Teacher Dashboard organizes primary tabs: Create, Library, Students (`ui/screens/teacher_dashboard/teacher_dashboard.py`).
  - Base dashboard layout, welcome, and system screens support navigation and consistency (`ui/screens/base_dashboard.py`, `ui/screens/welcome/welcome.py`).
- Create Tab (AI-assisted authoring)
  - Generate lesson plans, course structures, and materials via AI (`ui/screens/teacher/create_tab.py`).
  - Uses orchestration services to produce structured content packages (lessons, practice, assessments) (`database/services/content_orchestrator.py`, `database/services/comprehensive_content_generator.py`).
- Library Tab (materials management)
  - Manage and browse Content Library, Study Plans, Templates, Course Book (`ui/screens/teacher/library_tab.py`, `ui/screens/teacher/course_book_view.py`).
  - Create new content with AI (lessons, exercises, assessments) via `content_generation_service.py`, `exercise_generator_service.py`, `assessment_engine.py`.
  - Dialogs for study plans/book chapters (`ui/screens/teacher/study_plan_dialogs.py`, `ui/screens/teacher/book_chapter_dialogs.py`).
  - Content CRUD and hierarchy visualization (`database/services/content_service.py`, `ui/components/content_hierarchy_panel.py`).
- Students Tab (roster & actions)
  - View students, assign study plans, message, open profiles (`ui/screens/teacher/students_tab.py`).
  - Assign study plans and track progress (`database/services/study_plan_service.py`, `database/services/study_plan_assignments.py`, `database/services/study_plan_progress.py`).
  - Teacher messaging flows (`database/services/teacher_message_service.py`).
- Course Book
  - Build a course book with chapters, lessons, and materials; render hierarchical views (`ui/screens/teacher/course_book_view.py`).
  - Services for book storage and retrieval (`database/services/book_service.py`).
- Teacher AI Assistant
  - Context-aware assistant for planning, content refinement, and feedback (`ui/components/teacher_ai_assistant.py`, `ui/components/ai_assistant.py`, `ui/components/role_ai_assistant.py`).
  - Secure AI calls with guardrails (`database/services/secure_ai_service.py`).
- Analytics and Insights
  - Learning analytics services for progress and outcomes (`database/services/learning_analytics.py`, `database/services/analytics_service.py`, `database/services/analytics_visualization_service.py`).
  - UI components for charts (`ui/components/progress_chart.py`, `ui/screens/student_progress_charts.py`).
- Attachments and Exports
  - Attach and manage resources (`ui/components/attachments_panel.py`, `database/services/file_manager_service.py`).
  - Storage adapters including local and dummy S3 (`database/services/storage_adapters.py`, `config/settings.py` StorageConfig).
- Settings and Administration
  - AI configuration, invite codes, preferences, system diagnostics (`ui/screens/settings/*`).
  - AI configuration panel and types (`ui/components/ai_config_panel/*`, `ui/screens/settings/ai_config_tab.py`).
  - Invite code management (`ui/screens/settings/invite_codes_tab.py`, `database/services/invite_code_service.py`).
  - Preferences and system toggles (`ui/screens/settings/preferences_tab.py`, `ui/screens/settings/system_tab.py`).

## Student Functionality
- Student Dashboard and Navigation
  - Student dashboard and tabs (`ui/screens/student_dashboard.py`).
  - Learn, Practice, Lesson View, Connect tabs (`ui/screens/student/learn_tab.py`, `practice_tab.py`, `lesson_view.py`, `connect_tab.py`).
- Learn Tab
  - Resume sessions, view study path, progress indicators, quick actions (`ui/screens/student/learn_tab.py`).
  - Session resume and tracking services (`database/services/session_resume_service.py`, `database/services/learning_session_service.py`).
- Lesson View
  - Render organized lesson content, objectives, glossary, pitfalls (`ui/screens/student/lesson_view.py`).
  - Learning objectives, glossary, pitfalls services (`database/services/learning_objectives_service.py`, `glossary_service.py`, `pitfalls_service.py`).
- Practice Tab
  - Practice exercises generated or curated from AI (`ui/screens/student/practice_tab.py`, `database/services/exercise_generator_service.py`).
  - Parsers and fallback generators for robust practice (`database/services/exercise_generator/parsers.py`, `fallback_generators.py`).
- Connect Tab
  - Communication and support flows (`ui/screens/student/connect_tab.py`).
- Student AI Assistant
  - Tutoring and Q&A with secure guardrails (`ui/components/student_ai_assistant.py`).
  - Context-aware prompts, explanations, questions, summaries via `secure_ai_service.py` and `ai_service.py`.
- Book View
  - Student-facing course book consumption (`ui/screens/student/book_view.py`).
- Progress & Objectives
  - Objectives tracker and charts (`ui/components/objectives_tracker.py`, `ui/components/progress_chart.py`).
  - Analytics services (`database/services/learning_analytics.py`).

## Shared UI and System Behavior
- Base Screen and Layout
  - Standardized dashboard and screen base classes (`ui/screens/base_dashboard.py`, `ui/shared/*`).
- UI Services
  - Async UI wrapper for thread-safe operations (`ui/services/async_wrapper.py`).
  - UI service provider, email service, TTS manager (`ui/services/ui_service_provider.py`, `email_service.py`, `tts_manager.py`).
- Components and UX Utilities
  - Feedback banners, toast notifications, loading skeletons (`ui/components/feedback_banner.py`, `toast.py`, `loading.py`).
  - Context-aware detail panels and base panel system (`ui/components/context_aware_detail_panel.py`, `base_panel.py`).
  - Standardized form inputs and cards (`ui/components/input.py`, `button.py`, `card.py`, `standardized_entry.py`).
- Dialog Lifecycle
  - Non-blocking dialog patterns with proper focus and transient behavior (`tests/ui/test_dialog_lifecycle.py`).

## Data, Services, and Business Logic
- Study Plan Domain
  - CRUD, topics, assignments, progress (`database/services/study_plan_crud.py`, `study_plan_topics.py`, `study_plan_assignments.py`, `study_plan_progress.py`, `study_plan_service.py`).
  - Generators for AI study plans (`database/services/study_plan_generator.py`).
- Content Domain
  - Content CRUD and orchestration (`database/services/content_service.py`, `content_orchestrator.py`).
  - Rich content generation (`database/services/comprehensive_content_generator.py`).
- Practice and Assessment
  - Exercise generation, parsing, fallback (`database/services/exercise_generator_service.py`, `exercise_generator/*`).
  - Assessment engine and AI grading (`database/services/assessment_engine.py`, `ai_grading_service.py`, `submission_grading_service.py`).
  - Question bank management (`database/services/question_bank_service.py`).
- Sessions and Tracking
  - Learning session tracking (`database/services/learning_session_service.py`).
  - Resume and continuity (`database/services/session_resume_service.py`).
- Messaging and Communication
  - Teacher messaging service (`database/services/teacher_message_service.py`).
  - Communication system integration tests (`tests/integration/test_communication_system.py`).
- Analytics and Interventions
  - Analytics computation and visualization (`database/services/analytics_service.py`, `analytics_visualization_service.py`).
  - Intervention service for adaptive support (`database/services/intervention_service.py`).
- Security and Compliance
  - Security service and remote host validator (`database/services/security_service.py`, `security/remote_host_validator.py`).
  - AI audit service and security hooks (`database/services/ai_audit_service.py`).

## AI/LLM Functionality
- Capabilities Provided by AI
  - Lesson plan generation and refinement (`database/services/study_plan_generator.py`, `content_orchestrator.py`).
  - Content creation: lessons, exercises, assessments, glossaries, pitfalls, objectives (`comprehensive_content_generator.py`, `exercise_generator_service.py`, `assessment_engine.py`, `glossary_service.py`, `learning_objectives_service.py`, `pitfalls_service.py`).
  - Tutoring and Q&A: student/teacher assistants provide explanations, guided questions, feedback (`ui/components/student_ai_assistant.py`, `ui/components/teacher_ai_assistant.py`, `database/services/ai_tutor_service.py`).
  - AI coaching and adaptive curriculum (`database/services/ai_coach.py`, `adaptive_curriculum.py`).
  - AI refinement and question generation (`database/services/ai_refinement_service.py`, `ai_question_generator.py`).
  - AI grading and assessment analysis (`database/services/ai_grading_service.py`, `assessment_engine.py`, `qa_analysis_service.py`).
- AI Orchestration and Security
  - Central AI Service orchestrates providers, caching, failover, queueing, normalization (`database/services/ai_service.py`).
  - Secure AI Service enforces PII detection, role-based permissions, audit logging, compliance (`database/services/secure_ai_service.py`).
  - Provider Manager, Request Queue, Cache Manager, Usage Tracker, Performance Monitor (`database/services/ai/provider_manager.py`, `ai/request_queue.py`, `ai/cache_manager.py`, `ai/usage_tracker.py`, `ai/performance_monitor.py`).
- Supported Providers and Adapters
  - Ollama (`database/services/ai_providers/ollama_adapter.py`).
  - LM Studio (`database/services/ai_providers/lm_studio_adapter.py`).
  - OpenAI-compatible (direct) (`database/services/ai_providers/openai_adapter.py`, `openai_compatible.py`).
  - OpenRouter (`database/services/ai_providers/openrouter_adapter.py`).
  - Anthropic (via OpenRouter or direct key; configuration supported in `config/settings.py`).
  - Mock provider for tests (`database/services/ai_providers/mock_provider.py`).
- AI Configuration (Environment and Settings)
  - Centralized via `config/settings.py` `AIConfig` and `ConfigLoader`:
    - Provider selection: `AI_PROVIDER`, `LLM_PROVIDER` (`ollama|openai|openrouter|anthropic`).
    - Keys: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, optional `OLLAMA_API_KEY`.
    - Base URLs: `OPENAI_BASE_URL`, `OPENROUTER_BASE_URL`, `OLLAMA_BASE_URL`.
    - Models: `OPENAI_MODEL`, `OPENROUTER_MODEL`, `OLLAMA_MODEL`, `SLM_DEFAULT_AI_MODEL`, `SLM_AI_MODELS`.
    - Timeouts and retries: `AI_REQUEST_TIMEOUT`, `AI_TIMEOUT`, `AI_MAX_RETRIES`, `AI_RATE_LIMIT_PER_MINUTE`, `AI_RATE_LIMIT_PER_HOUR`, `MAX_CONCURRENT_AI_REQUESTS`.
    - Streaming and adapter options: `AI_ENABLE_STREAMING`, `AI_CHUNK_SIZE`, `AI_BACKOFF_FACTOR`, `AI_VERIFY_SSL`, `AI_ADAPTER_CACHE_TTL_MINUTES`.
    - Testing/mocks: `SLM_TEST_USE_MOCK_AI`, `SLM_AI_PROVIDERS_MOCK`, `AI_PROVIDER_TEST_MODE`, `TEST_AI_PROVIDER`, `TEST_AI_MODEL`.
  - Feature flags enhancing AI UX (`config/settings.py` FeatureFlagsConfig): `ENABLE_AI_COACHING`, `SLM_STUDENT_SCOPED_AI`, etc.
  - Testing configuration for providers (e.g., LM Studio, Ollama) with endpoints and models (`config/settings.py` TestingConfig).
- AI Usage in UI
  - Teacher and Student assistants call Secure AI Service with context-rich prompts (`ui/components/*ai_assistant*.py`).
  - Create/Library tabs integrate AI generation flows with content and study-plan services (`ui/screens/teacher/create_tab.py`, `ui/screens/teacher/library_tab.py`).

## Authentication, Roles, and Sessions
- Authentication Services and Models
  - Auth service, logger, exceptions, models (`auth/auth_service.py`, `auth/models.py`, `auth/auth_exceptions.py`, `auth/auth_logger.py`).
  - Role management for teacher/student permissions (`auth/role_manager.py`).
  - Session manager for login state and session TTL (`auth/session_manager.py`).
- Security Configuration
  - JWT config and secrets via `config/settings.py` SecurityConfig (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, token expiry settings).
  - Password policy, account lockouts, encryption settings.

## Settings and Configuration System
- Unified Configuration Loader
  - `.env` + environment variables with dataclass validation (`config/settings.py`).
  - Backward-compatible legacy interfaces preserved for older imports.
- Sub-configurations
  - Database, Security, AI, SMTP, Logging, UI, Cache, Performance, Compliance, Backup, Monitoring, Feature Flags, Testing, Directories, Content Generation, Storage.

## Error Handling and Compliance
- Error Boundaries and Logging
  - Structured logging configuration and helpers (`utils/logging_config.py`, `utils/logging_helpers.py`).
  - UI sanitization and decoupling tests ensure robust UI behavior (`tests/ui/test_ui_sanitization.py`, `tests/ui/test_ui_decoupling.py`).
- Compliance and Data Retention
  - FERPA/COPPA feature toggles and retention policy (`config/settings.py` ComplianceConfig).
  - AI audit logs and security monitoring (`database/services/ai_audit_service.py`).

## Testing and Quality Assurance
- UI Tests
  - Comprehensive coverage for dashboards, tabs, dialogs, assistants, sizing, toasts, feedback (`tests/ui/*.py`).
- Integration and Unit Tests
  - Services and domain modules validated across integration/unit (`tests/integration/**`, `tests/unit/**`).
- E2E Tests
  - Full teacher→student workflows, AI features with Ollama/LM Studio (`tests/e2e/**`).
  - Real-provider runs with mock disabled, environment overrides in tests.
- Headless and Async Patterns
  - Tkinter headless utilities and async wrappers validated (`tests/utils/tkinter_mocks.py`, `tests/ui/test_async_patterns.py`).

## Storage and Files
- Storage Modes
  - `local`, `dummy_s3`, `s3` with configurable root (`config/settings.py` StorageConfig: `SLM_STORAGE`, `SLM_STORAGE_ROOT`).
- File Manager
  - Attachments, exports, and file operations (`database/services/file_manager_service.py`).

## Performance and Caching
- Performance Controls
  - Rate limiting, monitoring, concurrency (`config/settings.py` PerformanceConfig).
- Caching
  - In-memory + Redis-compatible config; TTLs per domain (lessons, exercises, etc.) (`config/settings.py` CacheConfig).
  - AI cache service ensuring response reuse (`database/services/ai_cache_service.py`).

## Known UI Screens and Components Index
- Teacher Screens: `ui/screens/teacher/*.py` (create_tab, library_tab, students_tab, course_book_view, study_plan_dialogs, book_chapter_dialogs).
- Teacher Dashboard: `ui/screens/teacher_dashboard/teacher_dashboard.py` with validators and types.
- Student Screens: `ui/screens/student/*.py` (learn_tab, practice_tab, lesson_view, connect_tab, book_view).
- System/Settings: `ui/screens/settings/*` (ai_config_tab, invite_codes_tab, preferences_tab, system_tab, validators, types).
- Shared: `ui/screens/base_dashboard.py`, `ui/screens/welcome/welcome.py`, `ui/screens/active_session.py`, `ui/screens/learning_analytics.py`.
- Components: assistants, charts, panels, config panel, cards, inputs, toasts (`ui/components/**`).

## How Features Are Delivered (End-to-End)
- Teacher creates or refines study materials in Create/Library using AI services; content saved via `content_service.py`; study plans linked via `study_plan_service.py` and assigned in Students Tab.
- Student consumes assigned plans in Learn/Lesson/Practice, with session tracking and progress analytics; AI assistant provides tutoring under Secure AI guardrails.
- Settings allow administrators/teachers to configure providers and keys; feature flags tailor capabilities; storage and security settings govern persistence and compliance.
- Tests validate UI and service flows; E2E suites exercise real AI providers and full workflows to prevent regressions.

## AI Provider Configuration Quick Reference
- Minimal required environment variables (depending on chosen provider):
  - `AI_PROVIDER` and/or `LLM_PROVIDER`: one of `ollama|openai|openrouter|anthropic`.
  - `OPENAI_API_KEY` (OpenAI), `OPENROUTER_API_KEY` (OpenRouter), `ANTHROPIC_API_KEY` (Anthropic), `OLLAMA_BASE_URL` (Ollama), optional `OLLAMA_API_KEY`.
  - Model selection: `OPENAI_MODEL`, `OPENROUTER_MODEL`, `OLLAMA_MODEL`, `SLM_DEFAULT_AI_MODEL`, `SLM_AI_MODELS`.
  - Operational parameters: `AI_REQUEST_TIMEOUT`, `AI_TIMEOUT`, `AI_MAX_RETRIES`, `AI_RATE_LIMIT_PER_MINUTE`, `AI_RATE_LIMIT_PER_HOUR`, `MAX_CONCURRENT_AI_REQUESTS`, `AI_ENABLE_STREAMING`.
  - Testing toggles: `SLM_TEST_USE_MOCK_AI`, `SLM_AI_PROVIDERS_MOCK`, `AI_PROVIDER_TEST_MODE`, `TEST_AI_PROVIDER`, `TEST_AI_MODEL`.

## Notes on Security and Compliance for AI
- Secure AI calls anonymize PII, enforce role-based permissions, and record audit logs before invoking providers (`database/services/secure_ai_service.py`).
- Configuration flags: `ENABLE_PII_DETECTION`, `ENABLE_FERPA_COMPLIANCE`, `ENABLE_COPPA_COMPLIANCE`, with retention windows.

## Authentication and Access Control
- Roles: Teacher and Student roles enforced via `auth/role_manager.py`.
- JWT and session lifecycles configured via `config/settings.py` SecurityConfig and managed by `auth/session_manager.py`.

## Limitations and Extensibility
- Provider adapters are modular; adding new providers follows `ai_providers/base.py` interface and registration via `ai_providers/registry.py`.
- Feature flags allow enabling/disabling advanced features like AI coaching, spaced repetition, collaborative learning (`config/settings.py`).

---
This document reflects the current repository structure and capabilities discovered across UI, services, and tests, providing exhaustive coverage of Teacher and Student workflows and AI/LLM configuration.
