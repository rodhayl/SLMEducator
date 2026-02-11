# SLM Educator TRAE - Browser Test Guide

This document describes the step-by-step scenarios available for testing the SLM Educator GUI. It is optimized for LLM agents to verify functionality safely and thoroughly.

**Last Updated**: 2025-12-24 (Session Player Enhancements)  
**Application Version**: Full GUI with i18n support

## Prerequisites

- **Base URL**: `http://127.0.0.1:8080` (or `http://127.0.0.1:8000`)
- **Test Accounts**:
  - **Teacher/Admin**: `tester_unique_123` / `Password123!`
  - **Student**: Create via registration or use existing student account
- **Language**: Application supports English and Spanish (configurable in Settings)

---

## Testing Rules

### Timeout Policy
- **60 Second Limit**: Browser operations MUST be force-closed after 60 seconds if they don't succeed.
- **Alternative Approaches**: If an operation fails, try a different approach before giving up.
- **No Indefinite Waits**: NEVER wait indefinitely for browser operations.

### Recovery Protocol
When a test fails:
1. Document what was attempted
2. Try alternative approach (JS execution, direct navigation, etc.)
3. Proceed with next test scenario
4. Aggregate all failures for final report

---

## Application Structure Overview

### Pages (HTML Files)
| Page | Path | Description |
|------|------|-------------|
| Login | `/login.html` | Authentication entry point |
| Register | `/register.html` | New user registration |
| Dashboard | `/dashboard.html` | Main application hub (single-page) |
| Session Player | `/session_player.html` | Content consumption player |
| Assessment Taker | `/assessment_taker.html` | Quiz taking interface |
| Assessment Builder | `/assessment_builder.html` | Quiz creation tool |
| Study Plan Builder | `/study_plan_builder.html` | Drag-and-drop plan creator |
| Course Designer | `/course_designer.html` | AI-powered course wizard |
| Grading | `/grading.html` | Standalone grading dashboard |

### Dashboard Navigation (Sidebar)
| Nav Item | View ID | Role Access | Description |
|----------|---------|-------------|-------------|
| Overview (Panel) | `view-overview` | All | Stats, mastery, gamification |
| Inbox | `view-inbox` | All | Messaging system |
| My Library | `view-library` | All | Content management |
| Assessments | `view-assessments` | All | Quiz list and management |
| Grading | `view-grading` | Teacher/Admin | Embedded grading queue |
| Students | `view-students` | Teacher/Admin | Student roster management |
| Leaderboard | `view-leaderboard` | All | XP rankings |
| Help Queue | `view-help-queue` | All | Student assistance requests |
| Create Content | `view-create` | Teacher/Admin | Content creation hub |
| AI Tutor | `view-tutor` | All | AI chat interface |
| Settings | `view-settings` | All | User preferences |

---

## 1. Authentication Scenarios

### 1.1 Login Flow
**Goal**: Verify successful login and redirection.
1.  **Navigate** to `/login.html`.
2.  **Input** `#username` with `tester_unique_123`.
3.  **Input** `#password` with `Password123!`.
4.  **Click** `.btn-primary` ("Log In").
5.  **Verify** URL contains `/dashboard.html`.
6.  **Verify** element `#user-name-display` contains user's first name.

### 1.2 Registration Flow
**Goal**: Verify new user creation.
1.  **Navigate** to `/register.html`.
2.  **Select** Role (`Student` or `Teacher`).
3.  **Input** First Name, Last Name, Email, Username, Password.
4.  **Click** `Register` button.
5.  **Verify** redirection to `/login.html`.

### 1.3 Logout Flow
**Goal**: Verify session termination.
1.  **Click** `#logout-btn` in the sidebar.
2.  **Verify** redirection to `/login.html`.

### 1.4 Invalid Login
**Goal**: Verify error messages.
1.  **Navigate** to `/login.html`.
2.  **Input** invalid credentials.
3.  **Click** Login.
4.  **Verify** error message appears (not a generic 500 error).

### 1.5 Unauthorized Access
**Goal**: Verify auth guards.
1.  **Clear** authentication token (localStorage).
2.  **Navigate** directly to `/dashboard.html`.
3.  **Verify** redirection to `/login.html`.

---

## 2. Dashboard - Overview Section

### 2.1 Stats Cards Display
**Goal**: Verify all 6 stat cards load correctly.
1.  **Login** as user.
2.  **Verify** `#view-overview` is visible (default view).
3.  **Check** Stats Grid (`#stats-grid`) contains:
    - `#stat-active-students` - Active Students
    - `#stat-assessments-created` - Assessments Created
    - `#stat-average-score` - Average Score
    - `#stat-total-content` - Total Content
    - `#stat-total-study-time` - Total Study Time
    - `#stat-completed-lessons` - Completed Lessons

### 2.2 Continue Learning Card
**Goal**: Verify study plan progress card.
1.  **Check** `#continue-learning-card` visibility:
    - **If visible**: Student has active study plan assignment
    - **Verify** `#continue-plan-title` shows plan name
    - **Verify** `#progress-timeline` shows progress nodes
    - **Click** `#continue-btn` → Redirects to Session Player

### 2.3 Mastery & Spaced Repetition Widget
**Goal**: Verify mastery stats display.
1.  **Check** Mastery Card contains:
    - `#mastery-due-count` - Due for Review
    - `#mastery-avg` - Average Mastery %
    - `#mastery-mastered` - Mastered Items
    - `#mastery-progress` - In Progress Items
2.  **Click** "Start Review Session" button.
3.  **Verify** action triggers review mode.

### 2.4 Gamification Card
**Goal**: Verify gamification stats.
1.  **Check** `#gamification-card` contains:
    - `#gam-xp` - Total XP
    - `#gam-streak` - Day Streak 🔥
    - `#gam-longest-streak` - Best Streak 🏆
    - `#gam-badges` - Badge count 🎖️
    - `#gam-level-badge` - Current Level badge

### 2.5 Daily Goal Section
**Goal**: Verify daily goal UI.
1.  **Check** `#daily-goal-section` visible.
2.  **Verify** progress bar `#daily-goal-progress`.
3.  **Click** "Set Goal" button → Opens goal modal.

### 2.6 Daily Goal Modal
**Goal**: Verify daily goal setting workflow.
1.  **Click** "Set Goal" button in gamification card.
2.  **Verify** `#dailyGoalModal` opens.
3.  **Check** `#daily-goal-type` select has options:
    - Complete Lessons
    - Complete Exercises
    - Study Minutes
4.  **Input** target value `5` in `#daily-goal-target`.
5.  **Click** "Save Goal" button.
6.  **Verify** modal closes and `#daily-goal-progress` bar updates.

### 2.7 Continue Learning Actions
**Goal**: Verify continue learning card actions.
1.  **If** `#continue-learning-card` is visible:
    - **Click** "Continue" button → Redirects to Session Player
    - **Click** "View All" button → Shows plan tree/details

### 2.8 Recent Activity
**Goal**: Verify activity list loads.
1.  **Check** `#activity-list` contains recent items or "No activity" message.

---

## 3. Inbox & Messaging

### 3.1 Inbox View
**Goal**: Verify message listing and tabs.
1.  **Click** `Inbox` in sidebar.
2.  **Verify** `#view-inbox` visible.
3.  **Check** tabs present:
    - 📥 Inbox (active by default)
    - 📤 Sent
    - 📁 Archived
4.  **Verify** `#inbox-list` loads messages or empty state.

### 3.2 Inbox Folder Navigation
**Goal**: Verify folder switching.
1.  **Click** "Sent" tab.
2.  **Verify** sent messages load.
3.  **Click** "Archived" tab.
4.  **Verify** archived messages load.

### 3.3 Unread Badge
**Goal**: Verify unread count indicator.
1.  **Check** `#inbox-unread-badge` in sidebar.
2.  **Verify** badge shows count when unread messages exist.

### 3.4 Compose Message
**Goal**: Verify message sending.
1.  **Click** "Compose" button.
2.  **Verify** `#composeModal` opens.
3.  **Verify** recipient search with role filters (All, Students, Teachers).
4.  **Input** Subject and Body.
5.  **Click** `Send`.
6.  **Verify** success feedback and modal closes.

### 3.5 Message Actions
**Goal**: Verify per-message actions.
1.  **For each message in list**, verify action buttons:
    - ✅ Mark as Read
    - 📁 Archive
    - 🗑️ Delete
2.  **Click** each action and verify state changes.

### 3.6 Recipient Search Filter
**Goal**: Verify compose modal search and filtering.
1.  **Open** Compose Modal via "Compose" button.
2.  **Type** a name in `#compose-search`.
3.  **Verify** recipient list (`#compose-to`) filters to matching users.
4.  **Click** "Students" role filter button.
5.  **Verify** only students appear in list.
6.  **Click** "Teachers" role filter button.
7.  **Verify** only teachers appear in list.
8.  **Check** `#recipient-count` shows correct count.


## 4. My Library

### 4.1 Library View Toggle
**Goal**: Verify view switching.
1.  **Click** `My Library` in sidebar.
2.  **Verify** `#view-library` visible with `#library-section`.
3.  **Test View Toggle**:
    - **Click** `#view-flat-btn` (📋 Flat) → Verify grid layout
    - **Click** `#view-tree-btn` (🌳 Tree) → Verify hierarchical tree

### 4.2 Library Filters
**Goal**: Verify content filtering.
1.  **Select** from `#library-filter-type`:
    - All Types
    - Lesson
    - Exercise
    - Assessment
    - Q&A
    - Shared Q&A (Teacher only)
2.  **Verify** content list updates accordingly.

### 4.3 Library Stats
**Goal**: Verify stats cards.
1.  **Check** `#library-stats` contains:
    - `#lib-total` - Total Items
    - `#lib-lessons` - Lessons count
    - `#lib-exercises` - Exercises count
    - `#lib-assessments` - Assessments count

### 4.4 Content Card Actions
**Goal**: Verify per-item actions.
1.  **For each content card**, verify:
    - Type badge (LESSON, EXERCISE, ASSESSMENT)
    - Title and difficulty
    - Action buttons: 👁️ View, ▶️ Start, ✏️ Edit, 🗑️ Delete

### 4.5 Content View Modal
**Goal**: Verify content preview.
1.  **Click** 👁️ View on any content card.
2.  **Verify** `#contentViewModal` opens.
3.  **Check** modal shows:
    - `#content-view-type` - Type badge
    - `#content-view-difficulty` - Difficulty level
    - `#content-view-date` - Created date
    - `#content-view-body` - Content preview
4.  **Verify** action buttons:
    - 📖 Start Learning Session
    - ✏️ Edit
    - 🗑️ Delete

### 4.6 Content Edit Modal
**Goal**: Verify content editing.
1.  **Click** ✏️ Edit on content or in view modal.
2.  **Verify** `#contentEditModal` opens.
3.  **Modify** title, difficulty, or body.
4.  **Click** "Save Changes".
5.  **Verify** changes persist.

### 4.7 Student Q&A Modal
**Goal**: Verify student question creation.
1.  **Click** `#student-qa-btn` (+ New Question).
2.  **Verify** `#qaCreateModal` opens.
3.  **Input** title and question.
4.  **Optionally** click "🤖 Ask AI" for AI answer.
5.  **Click** "Save".
6.  **Verify** question appears in library.

---

## 5. Assessments Section

### 5.1 Assessment List
**Goal**: Verify assessment listing.
1.  **Click** `Assessments` in sidebar.
2.  **Verify** `#view-assessments` visible.
3.  **Check** assessment list loads (`#assessment-list`).
4.  **Verify** each assessment shows:
    - Title and description
    - Number of questions
    - Actions: "Start Quiz", "View Stats"

### 5.2 Create Assessment Link
**Goal**: Verify navigation to builder.
1.  **Click** "Create New Assessment" button.
2.  **Verify** navigation to `/assessment_builder.html`.

### 5.3 Take Assessment Flow
**Goal**: Verify assessment taking workflow.
1.  **Click** "Start Quiz" on an assessment.
2.  **Verify** redirect to `/assessment_taker.html?id=X`.
3.  **Answer** at least one question.
4.  **Click** "Submit Assessment".
5.  **Verify** results section appears with score.

### 5.4 View Assessment Stats
**Goal**: Verify stats viewing.
1.  **Click** "View Stats" on an assessment (if available).
2.  **Verify** stats display showing completion rate or average scores.


## 6. Grading (Teacher/Admin)

### 6.1 Embedded Grading Queue
**Goal**: Verify grading section loads.
1.  **Click** `Grading` in sidebar.
2.  **Verify** `#view-grading` visible.
3.  **Check** `#grading-list` loads submissions or empty state.

### 6.2 Standalone Grading Dashboard
**Goal**: Verify full grading page.
1.  **Navigate** to `/grading.html`.
2.  **Verify** "Grading Dashboard" header visible.
3.  **Check** `#submission-list` loads.
4.  **Select** a submission (if available).
5.  **Verify** `#grading-area` shows:
    - `#submission-title` - Student Name - Assessment Title
    - `#submission-status` - Status badge
    - `#answers-container` - Question/answer blocks
6.  **Verify** AI actions (`#ai-actions`) for AI-graded submissions:
    - "Accept All AI Suggestions" button
    - `#ai-summary` - AI summary text

### 6.3 Grade Submission
**Goal**: Verify grading workflow.
1.  **Input** score in `#grade-score`.
2.  **Input** feedback in `#grade-feedback`.
3.  **Click** "Submit Grade".
4.  **Verify** submission status updates.

---

## 7. Students Management (Teacher/Admin)

### 7.1 Student Roster
**Goal**: Verify student listing.
1.  **Click** `Students` in sidebar.
2.  **Verify** `#view-students` visible.
3.  **Check** student grid loads.
4.  **Verify** each student card shows:
    - Name and username
    - Level and XP
    - "View Details" button

### 7.2 Refresh Students
**Goal**: Verify refresh action.
1.  **Click** "Refresh" button.
2.  **Verify** student list reloads.

### 7.3 Student Detail Modal
**Goal**: Verify student details view.
1.  **Click** "View Details" on a student card.
2.  **Verify** `#studentDetailModal` opens.
3.  **Check** modal displays:
    - `#student-detail-name` - Full name
    - `#student-detail-username` - @username
    - `#student-detail-xp` - XP count
    - `#student-detail-level` - Current level
    - `#student-detail-streak` - 🔥 Streak
    - `#student-detail-badges` - Recent badges
4.  **Verify** "Send Message" button present.

### 7.4 Assign Study Plan to Student
**Goal**: Verify study plan assignment.
1.  **In Student Detail Modal**, select a study plan from `#student-assign-plan-select`.
2.  **Click** `#student-assign-plan-btn` ("Assign").
3.  **Verify** success message or assigned indicator.


## 8. Leaderboard

### 8.1 Leaderboard Display
**Goal**: Verify rankings display.
1.  **Click** `Leaderboard` in sidebar.
2.  **Verify** `#view-leaderboard` visible.
3.  **Check** ranking table shows:
    - Rank (#)
    - User name
    - XP amount
    - Level

### 8.2 Period Filter
**Goal**: Verify time period filtering.
1.  **Check** period selector (e.g., Weekly, Monthly, All Time).
2.  **Change** period selection.
3.  **Verify** rankings update.

---

## 9. Help Queue

### 9.1 Help Queue Display
**Goal**: Verify help request listing.
1.  **Click** `Help Queue` in sidebar.
2.  **Verify** `#view-help-queue` visible.
3.  **Check** request list loads.
4.  **Verify** each request shows:
    - Title/description
    - Priority badge (Normal/Urgent)
    - Sender information
    - Status (Open/Resolved)
    - Learning context (if available)

### 9.2 Student Help Request (Student Role)
**Goal**: Verify students can submit requests.
1.  **Login** as student.
2.  **Navigate** to Help Queue.
3.  **Verify** "Request Help" button visible.
4.  **Click** and fill request form.
5.  **Verify** request appears in queue.

### 9.3 Teacher Help Response (Teacher Role)
**Goal**: Verify teachers can respond.
1.  **Login** as teacher.
2.  **Select** a help request from `#help-queue-list`.
3.  **Verify** `#helpRequestModal` opens.

### 9.4 Help Request Detail Modal
**Goal**: Verify request details display.
1.  **After opening request**, verify modal shows:
    - `#help-request-status` - Status badge
    - `#help-request-priority` - Priority badge
    - `#help-request-subject` - Subject/Title
    - `#help-request-student` - Student name
    - `#help-request-content` - Request content
    - `#help-request-context` - Learning context (if available)
2.  **Verify** response section is visible:
    - `#help-response-text` - Response textarea
    - AI Draft Response button
    - Send Reply to Student button

### 9.5 AI Draft Response
**Goal**: Verify AI assistance in help responses.
1.  **Click** "🤖 AI Draft Response" button.
2.  **Verify** `#ai-draft-area` becomes visible with loading spinner.
3.  **Wait** for AI response to appear in `#ai-draft-content`.
4.  **Click** "✓ Use This Response".
5.  **Verify** AI text is copied to `#help-response-text`.

### 9.6 Send Help Response
**Goal**: Verify sending response to student.
1.  **Type** response in `#help-response-text`.
2.  **Click** "📧 Send Reply to Student".
3.  **Verify** success message appears.
4.  **Verify** request remains open (not auto-resolved).

### 9.7 Mark Request as Resolved
**Goal**: Verify resolution workflow.
1.  **Optionally** add notes in `#help-request-notes`.
2.  **Click** "✓ Mark as Resolved" button.
3.  **Verify** request status changes to "Resolved".
4.  **Verify** modal closes or updates.


## 10. Create Content (Teacher/Admin)

### 10.1 Create Content Hub
**Goal**: Verify creation options.
1.  **Click** `Create Content` in sidebar.
2.  **Verify** `#view-create` visible.
3.  **Check** Study Plan Builder card links to `/study_plan_builder.html`.
4.  **Verify** tabs present:
    - 🤖 AI Content Generator (default)
    - 📝 Manual Entry

### 10.2 AI Content Generator - Mode Selection
**Goal**: Verify generation modes.
1.  **Check** Mode Selector contains:
    - 📋 Study Plan - Multi-phase curriculum
    - 📚 Topic Package - Lesson + exercises + assessment (default)
    - 🏋️ Single Exercise - Quick practice problem
2.  **Select** each mode and verify appropriate fields display.

### 10.3 AI Content - Study Plan Mode
**Goal**: Verify study plan generation fields.
1.  **Select** "📋 Study Plan" mode.
2.  **Verify** `#study-plan-mode-fields` visible with:
    - Subject input
    - Grade Level dropdown
    - Duration (Weeks) input
    - Learning Objectives textarea

### 10.4 AI Content - Topic Mode
**Goal**: Verify topic generation fields.
1.  **Select** "📚 Topic Package" mode.
2.  **Verify** `#topic-mode-fields` visible with:
    - Subject and Topic Name inputs
    - Grade Level dropdown
    - Learning Objectives textarea
    - Content generation options:
      - ☑️ Lesson (include_lesson)
      - ☑️ Exercises (with count and difficulty options)
      - ☐ Assessment Questions (with count options)

### 10.5 AI Content - Exercise Mode
**Goal**: Verify single exercise fields.
1.  **Select** "🏋️ Single Exercise" mode.
2.  **Verify** appropriate simplified fields display.

### 10.6 Course Designer Link
**Goal**: Verify wizard access.
1.  **Check** "Open Course Designer Wizard" link.
2.  **Click** and verify navigation to `/course_designer.html`.

### 10.7 Manual Entry Tab
**Goal**: Verify manual creation form.
1.  **Click** "📝 Manual Entry" tab.
2.  **Verify** `#create-manual-form` appears with:
    - Title input (`name="title"`)
    - Content type selector (`name="content_type"`)
    - Body textarea (`name="content_body"`)
    - Publish button

### 10.8 AI Content Generation Execution
**Goal**: Verify AI content generation workflow.
1.  **Fill** Topic Mode fields (Subject, Topic Name, Learning Objectives).
2.  **Check** "Include Lesson" and "Include Exercises".
3.  **Click** "🤖 Generate Content" button.
4.  **Verify** loading state appears.
5.  **Wait** for generation to complete.
6.  **Verify** `#ai-content-generation-result` becomes visible with preview cards.

### 10.9 Save Generated Content
**Goal**: Verify saving AI-generated content.
1.  **After successful generation**, verify preview shows generated items.
2.  **Click** "💾 Save All" button.
3.  **Verify** success message appears.
4.  **Navigate** to Library and verify new content items appear.

### 10.10 Manual Entry Submission
**Goal**: Verify manual content publishing.
1.  **Click** "📝 Manual Entry" tab.
2.  **Fill** Title: "Test Manual Content".
3.  **Select** Type: "Lesson".
4.  **Fill** Body: "This is a test lesson created manually.".
5.  **Click** "Publish" button.
6.  **Verify** `#manual-entry-feedback` shows success message.
7.  **Navigate** to Library and verify content appears.

### 10.11 Save Options
**Goal**: Verify advanced save options.
1.  **Check** "Auto-save generated content to My Library" checkbox.
2.  **Check** "Add to existing Study Plan" checkbox.
3.  **Verify** `#study-plan-selector` appears.
4.  **Select** a study plan and phase.


## 11. AI Tutor

### 11.1 AI Tutor Interface
**Goal**: Verify chat interface.
1.  **Click** `AI Tutor` in sidebar.
2.  **Verify** `#view-tutor` visible.
3.  **Check** context selectors:
    - Study Plan dropdown (optional context)
    - Content dropdown (optional context)
4.  **Verify** chat area and input field.

### 11.2 AI Chat Conversation
**Goal**: Verify messaging.
1.  **Input** a question in chat input.
2.  **Click** "Send" (Enviar).
3.  **Verify** user message appears in `#chat-history`.
4.  **Verify** AI response loads (loading indicator, then response).

### 11.3 AI Tutor Context Selector
**Goal**: Verify content context filtering.
1.  **Check** `#tutor-study-plan` dropdown contains study plans.
2.  **Select** a study plan from dropdown.
3.  **Verify** `#tutor-content` dropdown updates with plan's content items.
4.  **Select** a content item.
5.  **Send** a question referencing the content.
6.  **Verify** AI response contains context-aware information.


## 12. Settings

### 12.1 Settings Tabs
**Goal**: Verify settings organization.
1.  **Click** `Settings` in sidebar.
2.  **Verify** `#view-settings` visible.
3.  **Check** tabs present:
    - Profile (default)
    - AI Configuration
    - Appearance

### 12.2 Profile Tab
**Goal**: Verify profile management.
1.  **Verify** Profile tab displays:
    - User avatar/name
    - Role badge
    - Account stats (joined date, badges)
    - Editable fields: First Name, Last Name, Email, Grade Level
2.  **Modify** a field and save.
3.  **Verify** success message.

### 12.3 AI Configuration Tab
**Goal**: Verify AI settings.
1.  **Click** AI Configuration tab.
2.  **Verify** settings include:
    - Provider dropdown (Ollama, LM Studio, etc.)
    - Model name input
    - Endpoint URL input
    - API Key input (optional)
    - Temperature slider
    - Max Tokens input
    - Preprocessing toggle
3.  **Click** "Test Connection" → Verify status message.
4.  **Click** "Save AI Config" → Verify inline success feedback.

### 12.4 Appearance Tab
**Goal**: Verify appearance settings.
1.  **Click** Appearance tab.
2.  **Verify** settings include:
    - Theme selector (`#app-theme`): Light/Dark/Auto
    - Language selector (`#app-lang`): English/Spanish
3.  **Toggle** theme → Verify UI updates in real-time.
4.  **Change** language → Verify i18n updates (labels change).

### 12.5 Profile Save Feedback
**Goal**: Verify profile editing persistence.
1.  **Modify** First Name field (`#profile-first-name`).
2.  **Click** "💾 Save Profile" button.
3.  **Verify** `#profile-feedback` shows success message.
4.  **Refresh** page and verify changes persist.

### 12.6 AI Test Connection Button
**Goal**: Verify connection testing.
1.  **Configure** AI provider and model.
2.  **Click** "🧪 Test Connection" button.
3.  **Verify** `#ai-test-result` shows:
    - Success message with green alert, OR
    - Error message with red alert

### 12.7 Fetch Models Button
**Goal**: Verify model discovery.
1.  **Select** Ollama or LM Studio provider.
2.  **Click** "🔄 Fetch" button.
3.  **Verify** `#ai-model-select` dropdown populates with available models.
4.  **Select** a model from dropdown.
5.  **Verify** `#ai-model` input updates.

### 12.8 Profile Badges Display
**Goal**: Verify badge section in profile.
1.  **Navigate** to Settings → Profile tab.
2.  **Verify** `#profile-badges-card` visible.
3.  **Check** `#profile-badges-count` shows badge count.
4.  **Verify** `#profile-badges-list` displays earned badges.


## 13. Session Player (Standalone)

### 13.1 Session Player Layout
**Goal**: Verify learning session interface.
1.  **Navigate** to `/session_player.html?id=[VALID_ID]`.
2.  **Verify** header shows:
    - "SLM Educator" brand with "Session Player" badge
    - Timer display
    - Exit button (X)

### 13.2 Content Display
**Goal**: Verify content rendering.
1.  **Check** `#content-display` loads content.
2.  **Verify** Markdown renders correctly.
3.  **Check** navigation buttons (Previous/Next if applicable).

### 13.3 Plan Sidebar (If Plan Context)
**Goal**: Verify plan navigation.
1.  **Navigate** with `plan_id` parameter.
2.  **Verify** `#plan-sidebar-container` visible.
3.  **Check** plan items listed with completion status.
4.  **Verify** `#plan-progress-text` shows "X/Y completed".

### 13.4 Notes Panel
**Goal**: Verify note-taking.
1.  **Click** "Notes" tab.
2.  **Verify** `#notes-panel` visible.
3.  **Type** in notes textarea.
4.  **Verify** auto-save indicator (`#notes-last-saved`).

### 13.5 Annotations Panel
**Goal**: Verify annotations.
1.  **Click** "Annotations" tab.
2.  **Verify** `#annotations-panel` visible.
3.  **Check** annotation input and list.
4.  **Add** annotation → Verify it appears.

### 13.6 Session Completion
**Goal**: Verify session end flow.
1.  **Click** "Complete" or "End Session".
2.  **Verify** End Session Modal appears.
3.  **Confirm** end → Verify progress saved and redirect.

### 13.7 Error Handling
**Goal**: Verify graceful errors.
1.  **Navigate** to `/session_player.html` (no ID).
2.  **Verify** error overlay appears:
    - "Session not found" message
    - "Return to Dashboard" button
3.  **Click** return button → Verify redirect.

### 13.8 Notes Server Sync
**Goal**: Verify notes sync to server (not just localStorage).
1.  **Start** a session with valid `content_id`.
2.  **Type** notes in `#session-notes` textarea.
3.  **Wait** 2 seconds for auto-save.
4.  **Verify** `#notes-save-status` shows "☁️ Synced" (server sync indicator).
5.  **Verify** `#notes-last-saved` shows timestamp.
6.  **End** session → **Verify** notes are included in session summary.
7.  **Navigate** back to same content.
8.  **Verify** previous notes are restored from server (not just localStorage).

### 13.9 Session Restore/Restart Modal
**Goal**: Verify restore vs restart prompt for previous sessions.
1.  **Complete** a session with notes (scenario 13.8).
2.  **Navigate** back to `/session_player.html?content_id=[SAME_ID]`.
3.  **Verify** `#sessionChoiceModal` opens with:
    - Title: "📚 Previous Session Found"
    - `#prev-session-date` - Previous session date
    - `#prev-session-notes-preview` - Preview of notes
    - "📥 Restore Notes" button
    - "🔄 Start Fresh" button
4.  **Click** "Restore Notes" → **Verify** notes loaded into textarea.
5.  **End** session and **Navigate** back again.
6.  **Click** "Start Fresh" → **Verify** empty notes textarea.

### 13.10 Session History API
**Goal**: Verify session history retrieval.
1.  **Complete** 2-3 sessions for same content with different notes.
2.  **Call** `GET /api/learning/history/{content_id}` via browser console:
    ```javascript
    fetch('/api/learning/history/1?limit=5', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    }).then(r => r.json()).then(console.log)
    ```
3.  **Verify** response contains array of sessions with:
    - `id` - Session IDs
    - `status` - "completed" or "active"
    - `notes` - Saved notes
    - `duration_minutes` - Session duration
4.  **Verify** sessions ordered by most recent first.

---

## 14. Assessment Taker (Standalone)

### 14.1 Assessment Taker Layout
**Goal**: Verify quiz interface.
1.  **Navigate** to `/assessment_taker.html?id=[VALID_ID]`.
2.  **Verify** header shows:
    - "SLM Educator" brand with "Assessment Taker" badge
    - Timer (`#timer`)
    - Exit button

### 14.2 Question Interface
**Goal**: Verify question display.
1.  **Check** `#assessment-title` and `#assessment-desc`.
2.  **Verify** `#questions-container` loads questions.
3.  **Check** each question has:
    - Question text
    - Answer input (text, multiple choice, etc.)

### 14.3 Submit Assessment
**Goal**: Verify submission.
1.  **Answer** all questions.
2.  **Click** `#submit-btn` (Submit Assessment).
3.  **Verify** `#results` area shows score/feedback.

### 14.4 Error Handling
**Goal**: Verify error states.
1.  **Navigate** to `/assessment_taker.html` (no ID or invalid ID).
2.  **Verify** `#error-overlay` appears:
    - "Assessment Not Found" message
    - "Return to Dashboard" button

---

## 15. Assessment Builder (Standalone)

### 15.1 Builder Layout
**Goal**: Verify builder interface.
1.  **Navigate** to `/assessment_builder.html`.
2.  **Verify** header shows:
    - "SLM Educator" brand with "Assessment Builder" badge
    - "Save & Publish" button
    - Exit button (X)

### 15.2 Assessment Metadata
**Goal**: Verify assessment setup.
1.  **Check** inputs for:
    - Assessment title
    - Description
    - Grading mode selector (AI-Assisted, Fully Automatic, Manual)
    - Time limit options

### 15.3 Question Management
**Goal**: Verify question creation.
1.  **Click** "+ Add Question" button.
2.  **Verify** new question block appears with:
    - Question text input
    - Question type selector (Multiple Choice, Short Answer, etc.)
    - Points input
    - Answer/options inputs based on type
3.  **Verify** question can be removed.

### 15.4 Rubric Modal
**Goal**: Verify rubric editing.
1.  **Click** "Edit Rubric" button.
2.  **Verify** `#rubricModal` opens.
3.  **Check** rubric criterion management.

### 15.5 Publish Assessment
**Goal**: Verify saving.
1.  **Fill** assessment details.
2.  **Add** at least one question.
3.  **Click** "Save & Publish".
4.  **Verify** success and redirect.

---

## 16. Study Plan Builder (Standalone)

### 16.1 Builder Layout
**Goal**: Verify builder interface.
1.  **Navigate** to `/study_plan_builder.html`.
2.  **Verify** header shows:
    - "SLM Educator" brand with "Study Plan Builder" badge
    - "Save Plan" button
    - Exit button (X)

### 16.2 Plan Metadata
**Goal**: Verify plan setup.
1.  **Check** inputs for:
    - `#plan-title` - Plan title
    - `#plan-desc` - Description textarea
    - `#plan-public` - Public toggle switch

### 16.3 Available Content Panel
**Goal**: Verify content source.
1.  **Check** left sidebar shows "Available Content".
2.  **Verify** `#source-content-list` loads library items.
3.  **Check** search filter (`#content-search`).

### 16.4 Phase Management
**Goal**: Verify phase creation.
1.  **Click** "+ Add Phase" button.
2.  **Verify** new phase card appears.
3.  **Input** phase name.
4.  **Verify** phase can be removed.

### 16.5 Drag and Drop
**Goal**: Verify content assignment.
1.  **Drag** content item from sidebar to phase area.
2.  **Verify** item "sticks" in the phase.
3.  **Verify** item can be reordered or removed.

### 16.6 Save Study Plan
**Goal**: Verify saving.
1.  **Fill** plan title and phases.
2.  **Click** "Save Plan".
3.  **Verify** success and redirect.

---

## 17. Course Designer (Standalone)

### 17.1 Wizard Layout
**Goal**: Verify AI wizard interface.
1.  **Navigate** to `/course_designer.html`.
2.  **Verify** header shows:
    - "SLM Educator" brand with "AI Course Designer" badge
    - "Back to Dashboard" button

### 17.2 Step Indicator
**Goal**: Verify progress steps.
1.  **Check** step indicator shows:
    - Step 1: Configure (active)
    - Step 2: Review
    - Step 3: Generate

### 17.3 Step 1: Configuration
**Goal**: Verify config form.
1.  **Check** `#stage-1` visible with form:
    - Subject/Topic input (required)
    - Grade Level dropdown
    - Duration (weeks) input
    - Source Material upload (optional)
2.  **Fill** required fields.
3.  **Click** "Next: Generate Outline".

### 17.4 Step 2: Outline Review
**Goal**: Verify outline display.
1.  **Verify** `#stage-2` appears after generation.
2.  **Check** AI-generated outline loads.
3.  **Verify** options:
    - "Start Over" button
    - "Confirm & Start Generation" button

### 17.5 Step 3: Generation
**Goal**: Verify cascade generation.
1.  **Click** "Confirm & Start Generation".
2.  **Verify** `#stage-3` shows generation progress.
3.  **Verify** completion state with created content.

---

## 18. Responsive & Visual Checks

### 18.1 Mobile Viewport
**Goal**: Verify responsive design.
1.  **Resize** browser to mobile width (375px).
2.  **Verify** sidebar collapses.
3.  **Check** `#sidebar-toggle` button visible in mobile topbar.
4.  **Click** toggle → Verify sidebar slides in.
5.  **Verify** content adjusts without horizontal scroll.

### 18.2 Theme Switching
**Goal**: Verify theme changes.
1.  **Navigate** to Settings > Appearance.
2.  **Toggle** to Light theme → Verify light colors.
3.  **Toggle** to Dark theme → Verify dark colors.
4.  **Toggle** to Auto → Verify follows system preference.

### 18.3 Language Switching (i18n)
**Goal**: Verify localization.
1.  **Navigate** to Settings > Appearance.
2.  **Change** language to Spanish.
3.  **Verify** all UI text updates to Spanish.
4.  **Change** back to English.
5.  **Verify** text reverts to English.

### 18.4 Style Consistency
**Goal**: Verify unified design.
1.  **Check** all pages for consistent:
    - Card styles (borders, shadows, padding)
    - Button sizes and colors
    - Typography and spacing
    - Form input styling
    - Empty state presentations

---

## 19. Role-Based Access Control

### 19.1 Student Role Restrictions
**Goal**: Verify student limitations.
1.  **Login** as Student.
2.  **Verify** hidden/disabled:
    - `#nav-create` (Create Content)
    - `#nav-grading` (Grading)
    - `#nav-students` (Students)
    - `#library-create-btn` (Create in Library)
    - `#library-filter-qa-shared` (Shared Q&A filter)
3.  **Verify** visible:
    - `#student-qa-btn` (New Question button)

### 19.2 Teacher Role Access
**Goal**: Verify teacher capabilities.
1.  **Login** as Teacher.
2.  **Verify** all navigation items visible.
3.  **Verify** content creation enabled.
4.  **Verify** grading and student management available.

---

## 20. Error Handling Scenarios

### 20.1 404 Content
**Goal**: Verify graceful handling.
1.  **Navigate** to `/session_player.html?id=99999`.
2.  **Verify** "Content not found" message.
3.  **Verify** "Return to Dashboard" button works.

### 20.2 Network Errors
**Goal**: Verify error feedback.
1.  **Disconnect** network (or stop backend).
2.  **Attempt** any API operation.
3.  **Verify** user-friendly error message appears.

### 20.3 Form Validation
**Goal**: Verify input validation.
1.  **Submit** forms with empty required fields.
2.  **Verify** validation errors display.
3.  **Verify** form doesn't submit until valid.

---

## Test Execution Summary Template

```markdown
## Test Run: [DATE] - [TESTER]

### Environment
- URL: http://127.0.0.1:8080
- Browser: [Chrome/Firefox/etc]
- User Role: [Teacher/Student]
- Language: [English/Spanish]

### Passed ✅
- [ ] 1.1 Login Flow
- [ ] 2.1 Stats Cards Display
- [ ] 3.1 Inbox View
- [ ] ... (continue for all scenarios)

### Failed ❌
- [ ] X.X Test Name - **Reason**: Description of failure

### Blocked/Skipped ⏭️
- [ ] X.X Test Name - **Reason**: Why blocked/skipped

### Issues Found
1. **[SEVERITY]** Issue description
   - **Location**: Page/Component
   - **Steps**: How to reproduce
   - **Expected**: What should happen
   - **Actual**: What happened

### Notes
- Any additional observations or recommendations
```

---

## Quick Reference: Element Selectors

### Sidebar Navigation
| Element | Selector |
|---------|----------|
| Dashboard Tab | `[data-view="overview"]` |
| Inbox Tab | `[data-view="inbox"]` |
| Library Tab | `[data-view="library"]` |
| Assessments Tab | `[data-view="assessments"]` |
| Grading Tab | `[data-view="grading"]` |
| Students Tab | `[data-view="students"]` |
| Leaderboard Tab | `[data-view="leaderboard"]` |
| Help Queue Tab | `[data-view="help-queue"]` |
| Create Tab | `[data-view="create"]` |
| Tutor Tab | `[data-view="tutor"]` |
| Settings Tab | `[data-view="settings"]` |

### Common Controls
| Element | Selector |
|---------|----------|
| User Name Display | `#user-name-display` |
| Logout Button | `#logout-btn` |
| Mobile Menu Toggle | `#sidebar-toggle` |
| Inbox Unread Badge | `#inbox-unread-badge` |

### Modals
| Modal | Selector |
|-------|----------|
| Content View | `#contentViewModal` |
| Content Edit | `#contentEditModal` |
| Q&A Create | `#qaCreateModal` |
| Compose Message | `#composeModal` |
| Rubric Editor | `#rubricModal` |
