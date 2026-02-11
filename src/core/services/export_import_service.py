"""
Export/Import Service for SLMEducator - Handles data export and import functionality.

This module provides comprehensive export/import capabilities including:
- Study plan export/import (JSON/Markdown/PDF)
- Content export/import with validation
- Assessment export/import
- Bulk data operations
- Schema validation and version compatibility
"""

import json
import importlib
from datetime import datetime
from typing import Dict, Any, Optional, cast, TYPE_CHECKING
import logging
import zipfile

from ..models import (
    User,
    StudyPlan,
    StudyPlanContent,
    Content,
    Assessment,
    AssessmentQuestion,
    StudentStudyPlan,
    LearningSession,
    QuestionType,
    ContentType,
    AssessmentSubmission,
    AuditLog,
    AuthAttempt,
    encrypt_data,
    extract_phases,
)
from ..exceptions import ValidationError, ConfigurationError
from .database import DatabaseService

markdown_module = cast(Any, importlib.import_module("markdown"))

if TYPE_CHECKING:
    from reportlab.platypus import Flowable

# Import PDF generation if available
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ExportImportService:
    """Service for handling data export and import operations."""

    def __init__(self, db_service: DatabaseService):
        """Initialize export/import service."""
        self.db = db_service
        self.logger = logging.getLogger(__name__)
        self.current_schema_version = "1.0"

    def export_study_plan_json(
        self,
        study_plan: StudyPlan,
        include_content: bool = True,
        include_assessments: bool = True,
        include_analytics: bool = False,
    ) -> Dict[str, Any]:
        """
        Export study plan to JSON format.

        Args:
            study_plan: Study plan to export
            include_content: Include associated content
            include_assessments: Include associated assessments
            include_analytics: Include analytics data

        Returns:
            JSON data structure
        """
        # Ensure we have a valid session for accessing relationships
        with self.db.get_session() as session:
            # If study_plan is detached, re-attach it or get fresh copy
            if not session.object_session(study_plan):
                refreshed_study_plan = (
                    session.query(StudyPlan).filter_by(id=study_plan.id).first()
                )
                if refreshed_study_plan is None:
                    raise ValueError("Study plan not found")
                study_plan = refreshed_study_plan

            study_plan_id = getattr(study_plan, "id", None)
            if study_plan_id is None:
                raise ValueError("Study plan missing id")

            creator = getattr(study_plan, "creator", None)
            creator_username = getattr(creator, "username", None) or ""
            creator_full_name = getattr(creator, "full_name", None) or ""

            created_at = getattr(study_plan, "created_at", None)
            updated_at = getattr(study_plan, "updated_at", None)
            phases = getattr(study_plan, "phases", None) or []
            metadata = getattr(study_plan, "decrypted_metadata", None) or {}

            data: Dict[str, Any] = {
                "schema_version": self.current_schema_version,
                "export_date": datetime.now().isoformat(),
                "type": "study_plan",
                "study_plan": {
                    "id": study_plan_id,
                    "title": getattr(study_plan, "title", None) or "",
                    "description": getattr(study_plan, "description", None) or "",
                    "phases": phases,
                    "metadata": metadata,
                    "is_public": bool(getattr(study_plan, "is_public", False)),
                    "created_at": created_at.isoformat() if created_at else None,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                    "creator": {
                        "username": creator_username,
                        "full_name": creator_full_name,
                    },
                },
            }

            if include_content:
                associations = (
                    session.query(StudyPlanContent)
                    .filter(StudyPlanContent.study_plan_id == study_plan_id)
                    .order_by(
                        StudyPlanContent.phase_index, StudyPlanContent.order_index
                    )
                    .all()
                )
                content_items: list[Dict[str, Any]] = []
                for assoc in associations:
                    content = getattr(assoc, "content", None)
                    if content is None:
                        continue

                    content_type_obj = getattr(content, "content_type", None)
                    content_type_value = (
                        content_type_obj.value
                        if content_type_obj is not None
                        and getattr(content_type_obj, "value", None) is not None
                        else str(content_type_obj)
                    )
                    content_created_at = getattr(content, "created_at", None)
                    content_updated_at = getattr(content, "updated_at", None)

                    content_data = {
                        "id": getattr(content, "id", None),
                        "type": content_type_value,
                        "title": getattr(content, "title", None) or "",
                        "difficulty": int(getattr(content, "difficulty", 1)),
                        "estimated_time_min": int(
                            getattr(content, "estimated_time_min", 15)
                        ),
                        "phase_index": int(getattr(assoc, "phase_index", 0)),
                        "order_index": int(getattr(assoc, "order_index", 0)),
                        "ai_enhanced": False,
                        "created_at": (
                            content_created_at.isoformat()
                            if content_created_at
                            else None
                        ),
                        "updated_at": (
                            content_updated_at.isoformat()
                            if content_updated_at
                            else None
                        ),
                    }

                    # Include content data based on type
                    if content_type_obj == ContentType.LESSON:
                        content_data["content_data"] = getattr(
                            content, "decrypted_content_data", None
                        )
                    elif content_type_obj == ContentType.ASSESSMENT:
                        # Don't include assessment content data, will be handled separately
                        content_data["assessment_reference"] = True

                    content_items.append(content_data)

                data["content"] = content_items

            if include_assessments:
                assessments = (
                    session.query(Assessment)
                    .filter_by(study_plan_id=study_plan_id)
                    .all()
                )
                data["assessments"] = []
                for assessment in assessments:
                    assessment_data = self.export_assessment_json(
                        assessment, include_questions=True
                    )
                    data["assessments"].append(assessment_data)

            if include_analytics:
                # Add basic analytics
                student_assignments = (
                    session.query(StudentStudyPlan)
                    .filter_by(study_plan_id=study_plan.id)
                    .count()
                )
                data["analytics"] = {
                    "student_assignments": student_assignments,
                    "content_count": len(data.get("content", [])),
                    "assessment_count": len(data.get("assessments", [])),
                }

        return data

    def export_study_plan_markdown(
        self, study_plan: StudyPlan, include_content: bool = True
    ) -> str:
        """
        Export study plan to Markdown format.

        Args:
            study_plan: Study plan to export
            include_content: Include associated content

        Returns:
            Markdown content
        """
        # Ensure we have a valid session for accessing relationships
        with self.db.get_session() as session:
            # If study_plan is detached, re-attach it or get fresh copy
            if not session.object_session(study_plan):
                refreshed_study_plan = (
                    session.query(StudyPlan).filter_by(id=study_plan.id).first()
                )
                if refreshed_study_plan is None:
                    raise ValueError("Study plan not found")
                study_plan = refreshed_study_plan

            md_lines = []

            # Header
            md_lines.append(f"# {getattr(study_plan, 'title', None) or ''}")
            md_lines.append("")

            # Metadata
            created_at = getattr(study_plan, "created_at", None)
            updated_at = getattr(study_plan, "updated_at", None)
            creator = getattr(study_plan, "creator", None)
            creator_full_name = getattr(creator, "full_name", None) or ""
            creator_username = getattr(creator, "username", None) or ""
            is_public = bool(getattr(study_plan, "is_public", False))

            md_lines.append(
                f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M') if created_at else ''}"
            )
            md_lines.append(
                f"**Updated:** {updated_at.strftime('%Y-%m-%d %H:%M') if updated_at else ''}"
            )
            md_lines.append(f"**Creator:** {creator_full_name} (@{creator_username})")
            md_lines.append(f"**Public:** {'Yes' if is_public else 'No'}")
            md_lines.append("")

            # Description
            description = getattr(study_plan, "description", None) or ""
            if description:
                md_lines.append("## Description")
                md_lines.append(description)
                md_lines.append("")

            # Phases
            phases_raw = getattr(study_plan, "phases", None) or []
            if phases_raw:
                md_lines.append("## Learning Phases")
                phases = extract_phases(phases_raw)
                for i, phase in enumerate(phases, 1):
                    md_lines.append(
                        f"### Phase {i}: {phase.get('name', phase.get('title', 'Unnamed Phase'))}"
                    )
                    md_lines.append(
                        f"**Duration:** {phase.get('duration_weeks', 'N/A')} weeks"
                    )
                    md_lines.append(f"**Objectives:** {phase.get('objectives', 'N/A')}")
                    md_lines.append("")

            # Content
            if include_content:
                study_plan_id = getattr(study_plan, "id", None)
                if study_plan_id is not None:
                    associations = (
                        session.query(StudyPlanContent)
                        .filter(StudyPlanContent.study_plan_id == study_plan_id)
                        .order_by(
                            StudyPlanContent.phase_index, StudyPlanContent.order_index
                        )
                        .all()
                    )
                else:
                    associations = []

                if associations:
                    md_lines.append("## Content")
                    for assoc in associations:
                        content = getattr(assoc, "content", None)
                        if content is None:
                            continue

                        content_title = getattr(content, "title", None) or ""
                        content_type_obj = getattr(content, "content_type", None)
                        content_type_value = (
                            content_type_obj.value
                            if content_type_obj is not None
                            and getattr(content_type_obj, "value", None) is not None
                            else str(content_type_obj)
                        )
                        difficulty = int(getattr(content, "difficulty", 1))
                        estimated_time_min = int(
                            getattr(content, "estimated_time_min", 15)
                        )

                        md_lines.append(f"### {content_title}")
                        md_lines.append(f"**Type:** {content_type_value}")
                        md_lines.append(f"**Difficulty:** {difficulty}/10")
                        md_lines.append(
                            f"**Estimated Time:** {estimated_time_min} minutes"
                        )

                        if content_type_obj == ContentType.LESSON:
                            content_data = (
                                getattr(content, "decrypted_content_data", None) or {}
                            )
                            lesson_text = content_data.get("content")
                            if isinstance(lesson_text, str) and lesson_text:
                                md_lines.append("")
                                md_lines.append(lesson_text)

                        md_lines.append("")

            return "\n".join(md_lines)

    def export_study_plan_pdf(
        self, study_plan: StudyPlan, output_path: str, include_content: bool = True
    ) -> bool:
        """
        Export study plan to PDF format.

        Args:
            study_plan: Study plan to export
            output_path: Output file path
            include_content: Include associated content

        Returns:
            True if successful, False otherwise

        Raises:
            ConfigurationError: If PDF generation is not available
        """
        if not PDF_AVAILABLE:
            raise ConfigurationError("PDF generation not available. Install reportlab.")

        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story: list["Flowable"] = []

            # Title
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center alignment
            )
            story.append(
                Paragraph(getattr(study_plan, "title", None) or "", title_style)
            )
            story.append(Spacer(1, 12))

            # Metadata
            created_at = getattr(study_plan, "created_at", None)
            updated_at = getattr(study_plan, "updated_at", None)
            creator = getattr(study_plan, "creator", None)
            creator_full_name = getattr(creator, "full_name", None) or ""
            creator_username = getattr(creator, "username", None) or ""
            is_public = bool(getattr(study_plan, "is_public", False))
            metadata_text = f"""
            <b>Created:</b> {created_at.strftime('%Y-%m-%d %H:%M') if created_at else ''}<br/>
            <b>Updated:</b> {updated_at.strftime('%Y-%m-%d %H:%M') if updated_at else ''}<br/>
            <b>Creator:</b> {creator_full_name} (@{creator_username})<br/>
            <b>Public:</b> {'Yes' if is_public else 'No'}
            """
            story.append(Paragraph(metadata_text, styles["Normal"]))
            story.append(Spacer(1, 12))

            # Description
            description = getattr(study_plan, "description", None) or ""
            if description:
                story.append(Paragraph("Description", styles["Heading2"]))
                story.append(Paragraph(description, styles["Normal"]))
                story.append(Spacer(1, 12))

            # Phases
            phases_raw = getattr(study_plan, "phases", None) or []
            if phases_raw:
                story.append(Paragraph("Learning Phases", styles["Heading2"]))
                phases = extract_phases(phases_raw)
                for i, phase in enumerate(phases, 1):
                    phase_name = phase.get("name", phase.get("title", "Unnamed Phase"))
                    story.append(
                        Paragraph(f"Phase {i}: {phase_name}", styles["Heading3"])
                    )
                    phase_text = f"""
                    <b>Duration:</b> {phase.get('duration_weeks', 'N/A')} weeks<br/>
                    <b>Objectives:</b> {phase.get('objectives', 'N/A')}
                    """
                    story.append(Paragraph(phase_text, styles["Normal"]))
                    story.append(Spacer(1, 6))

            # Content
            if include_content:
                with self.db.get_session() as session:
                    study_plan_id = getattr(study_plan, "id", None)
                    if study_plan_id is not None:
                        associations = (
                            session.query(StudyPlanContent)
                            .filter(StudyPlanContent.study_plan_id == study_plan_id)
                            .order_by(
                                StudyPlanContent.phase_index,
                                StudyPlanContent.order_index,
                            )
                            .all()
                        )
                    else:
                        associations = []

                    if associations:
                        story.append(PageBreak())
                        story.append(Paragraph("Content", styles["Heading2"]))

                        for assoc in associations:
                            content = getattr(assoc, "content", None)
                            if content is None:
                                continue

                            content_title = getattr(content, "title", None) or ""
                            story.append(Paragraph(content_title, styles["Heading3"]))

                            content_type_obj = getattr(content, "content_type", None)
                            content_type_value = (
                                content_type_obj.value
                                if content_type_obj is not None
                                and getattr(content_type_obj, "value", None) is not None
                                else str(content_type_obj)
                            )
                            difficulty = int(getattr(content, "difficulty", 1))
                            estimated_time_min = int(
                                getattr(content, "estimated_time_min", 15)
                            )
                            content_info = f"""
                            <b>Type:</b> {content_type_value}<br/>
                            <b>Difficulty:</b> {difficulty}/10<br/>
                            <b>Estimated Time:</b> {estimated_time_min} minutes
                            """
                            story.append(Paragraph(content_info, styles["Normal"]))

                            if content_type_obj == ContentType.LESSON:
                                content_data = (
                                    getattr(content, "decrypted_content_data", None)
                                    or {}
                                )
                                lesson_text = content_data.get("content")
                                if isinstance(lesson_text, str) and lesson_text:
                                    story.append(Spacer(1, 6))
                                    # Convert markdown to basic HTML for PDF
                                    html_content = markdown_module.markdown(lesson_text)
                                    story.append(
                                        Paragraph(html_content, styles["Normal"])
                                    )

                            story.append(Spacer(1, 12))

            doc.build(story)
            self.logger.info(f"Study plan exported to PDF: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"PDF export failed: {e}")
            return False

    def export_assessment_json(
        self,
        assessment: Assessment,
        include_questions: bool = True,
        include_submissions: bool = False,
    ) -> Dict[str, Any]:
        """
        Export assessment to JSON format.

        Args:
            assessment: Assessment to export
            include_questions: Include assessment questions
            include_submissions: Include submission data (privacy sensitive)

        Returns:
            JSON data structure
        """
        creator = getattr(assessment, "created_by", None)
        creator_username = getattr(creator, "username", None) or ""
        creator_full_name = getattr(creator, "full_name", None) or ""
        created_at = getattr(assessment, "created_at", None)
        updated_at = getattr(assessment, "updated_at", None)

        data: Dict[str, Any] = {
            "schema_version": self.current_schema_version,
            "export_date": datetime.now().isoformat(),
            "type": "assessment",
            "assessment": {
                "id": getattr(assessment, "id", None),
                "title": getattr(assessment, "title", None) or "",
                "description": getattr(assessment, "description", None),
                "instructions": getattr(assessment, "instructions", None),
                "time_limit_minutes": getattr(assessment, "time_limit_minutes", None),
                "max_attempts": int(getattr(assessment, "max_attempts", 1)),
                "passing_score": int(getattr(assessment, "passing_score", 70)),
                "total_points": int(getattr(assessment, "total_points", 100)),
                "is_published": bool(getattr(assessment, "is_published", False)),
                "created_at": created_at.isoformat() if created_at else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "creator": {
                    "username": creator_username,
                    "full_name": creator_full_name,
                },
            },
        }

        if include_questions:
            with self.db.get_session() as session:
                questions = (
                    session.query(AssessmentQuestion)
                    .filter_by(assessment_id=assessment.id)
                    .order_by(AssessmentQuestion.order_index)
                    .all()
                )

                questions_list: list[Dict[str, Any]] = []
                for question in questions:
                    question_type_obj = getattr(question, "question_type", None)
                    question_type_value = (
                        question_type_obj.value
                        if question_type_obj is not None
                        and getattr(question_type_obj, "value", None) is not None
                        else str(question_type_obj)
                    )
                    question_created_at = getattr(question, "created_at", None)
                    question_updated_at = getattr(question, "updated_at", None)
                    question_data = {
                        "id": getattr(question, "id", None),
                        "question_text": getattr(question, "question_text", None) or "",
                        "question_type": question_type_value,
                        "points": int(getattr(question, "points", 0)),
                        "order_index": int(getattr(question, "order_index", 0)),
                        "options": getattr(question, "options", None),
                        "content_metadata": getattr(question, "content_metadata", None),
                        "created_at": (
                            question_created_at.isoformat()
                            if question_created_at
                            else None
                        ),
                        "updated_at": (
                            question_updated_at.isoformat()
                            if question_updated_at
                            else None
                        ),
                    }

                    # Don't include correct answer for security
                    # question_data["correct_answer"] = question.get_decrypted_correct_answer()

                    questions_list.append(question_data)

                data["questions"] = questions_list

        creator_role_value = getattr(getattr(creator, "role", None), "value", None)
        if include_submissions and creator_role_value == "admin":
            # Only include submissions for admin exports
            with self.db.get_session() as session:
                submissions = (
                    session.query(AssessmentSubmission)
                    .filter_by(assessment_id=assessment.id)
                    .all()
                )

                submissions_list: list[Dict[str, Any]] = []
                for submission in submissions:
                    student = getattr(submission, "student", None)
                    student_name = getattr(student, "full_name", None) or ""
                    status_obj = getattr(submission, "status", None)
                    status_value = (
                        status_obj.value
                        if status_obj is not None
                        and getattr(status_obj, "value", None) is not None
                        else str(status_obj)
                    )
                    started_at = getattr(submission, "started_at", None)
                    submitted_at = getattr(submission, "submitted_at", None)
                    submission_data = {
                        "id": getattr(submission, "id", None),
                        "student_name": student_name,
                        "score": getattr(submission, "score", None),
                        "total_points": getattr(submission, "total_points", None),
                        "status": status_value,
                        "started_at": started_at.isoformat() if started_at else None,
                        "submitted_at": (
                            submitted_at.isoformat() if submitted_at else None
                        ),
                        "time_spent_minutes": getattr(
                            submission, "time_spent_minutes", None
                        ),
                    }
                    submissions_list.append(submission_data)

                data["submissions"] = submissions_list

        return data

    def import_study_plan_json(
        self,
        data: Dict[str, Any],
        user: User | Dict[str, Any],
        validate_schema: bool = True,
    ) -> StudyPlan:
        """
        Import study plan from JSON data.

        Args:
            data: JSON data structure
            user: User importing the study plan
            validate_schema: Validate schema version

        Returns:
            Imported study plan

        Raises:
            ValidationError: If validation fails
        """
        if validate_schema:
            self._validate_schema_version(data.get("schema_version", "1.0"))

        if data.get("type") != "study_plan":
            raise ValidationError("Invalid data type for study plan import")

        study_plan_data = data.get("study_plan", {})
        if not study_plan_data:
            raise ValidationError("No study plan data found")

        # Ensure user has a valid session
        with self.db.get_session() as session:
            # If user is a dict, get the actual User object from database
            if isinstance(user, dict):
                raw_user_id = user.get("id")
                if not isinstance(raw_user_id, int):
                    raise ValueError("User missing id")
                fresh_user = session.query(User).filter_by(id=raw_user_id).first()
                if not fresh_user:
                    raise ValueError("User not found")
                user = fresh_user
            # If user is detached, get fresh copy
            elif not session.object_session(user):
                # Try to get user by ID, if that fails, try by username
                if hasattr(user, "id"):
                    fresh_user = session.query(User).filter_by(id=user.id).first()
                elif hasattr(user, "username"):
                    fresh_user = (
                        session.query(User).filter_by(username=user.username).first()
                    )
                else:
                    raise ValueError("Invalid user object")

                if not fresh_user:
                    raise ValueError("User not found")
                user = fresh_user

            user_id = getattr(user, "id", None)
            if user_id is None:
                raise ValueError("User missing id")

            # Create study plan
            study_plan = StudyPlan(
                title=study_plan_data.get("title", "Imported Study Plan"),
                description=study_plan_data.get("description", ""),
                phases=study_plan_data.get("phases", []),
                content_metadata=encrypt_data(
                    json.dumps(study_plan_data.get("metadata", {}))
                ),
                is_public=False,  # Imported plans are private by default
                creator_id=user_id,
            )

            session.add(study_plan)
            session.flush()  # Get ID for content creation

            study_plan_id = getattr(study_plan, "id", None)
            if study_plan_id is None:
                raise ValueError("Study plan missing id after flush")

            # Import content if available
            if "content" in data:
                for content_item in data["content"]:
                    try:
                        phase_index = content_item.get("phase_index", 0)
                        order_index = content_item.get("order_index", 0)
                        content = Content(
                            study_plan_id=study_plan_id,
                            content_type=ContentType(
                                content_item.get("type", "lesson")
                            ),
                            title=content_item.get("title", "Untitled Content"),
                            content_data=encrypt_data(
                                json.dumps(content_item.get("content_data", {}))
                            ),
                            difficulty=content_item.get("difficulty", 5),
                            estimated_time_min=content_item.get(
                                "estimated_time_min", 30
                            ),
                        )
                        session.add(content)
                        session.flush()

                        content_id = getattr(content, "id", None)
                        if content_id is not None:
                            assoc = StudyPlanContent(
                                study_plan_id=study_plan_id,
                                content_id=content_id,
                                phase_index=(
                                    int(phase_index)
                                    if isinstance(phase_index, int)
                                    else 0
                                ),
                                order_index=(
                                    int(order_index)
                                    if isinstance(order_index, int)
                                    else 0
                                ),
                            )
                            session.add(assoc)
                    except Exception as e:
                        self.logger.warning(f"Failed to import content: {e}")
                        continue

            # Import assessments if available
            if "assessments" in data:
                for assessment_data in data["assessments"]:
                    try:
                        self._import_assessment_json(
                            assessment_data, study_plan_id, user
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to import assessment: {e}")
                        continue

            session.commit()
            # Get the title before the session closes to avoid detached instance issues
            study_plan_title = study_plan.title
            import_username = getattr(user, "username", None) or "unknown"

        self.logger.info(
            f"Study plan imported: {study_plan_title} by {import_username}"
        )
        return study_plan

    def import_study_plan_markdown(self, content: str, user: User) -> StudyPlan:
        """
        Import study plan from Markdown content.

        Args:
            content: Markdown content
            user: User importing the study plan

        Returns:
            Imported study plan

        Raises:
            ValidationError: If validation fails
        """
        lines = content.strip().split("\n")

        # Parse title
        title = "Imported Study Plan"
        description = ""
        phases = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("## Description"):
                # Collect description lines
                i += 1
                desc_lines = []
                while i < len(lines) and not (
                    lines[i].strip().startswith("##")
                    or lines[i].strip().startswith("# ")
                ):
                    if lines[i].strip():
                        desc_lines.append(lines[i].strip())
                    i += 1
                description = " ".join(desc_lines)
                continue
            elif line.startswith("## Learning Phases"):
                # Parse phases
                i += 1
                while i < len(lines):
                    if lines[i].strip().startswith("### Phase"):
                        phase_name = (
                            lines[i].strip()[lines[i].strip().find(":") + 1 :].strip()
                        )
                        phase = {
                            "name": phase_name,
                            "duration_weeks": 1,
                            "objectives": "",
                        }

                        # Look for phase details
                        i += 1
                        while i < len(lines) and not (
                            lines[i].strip().startswith("###")
                            or lines[i].strip().startswith("##")
                        ):
                            if lines[i].strip().startswith("**Duration:**"):
                                start_idx = lines[i].strip().find("**Duration:**") + 13
                                duration_str = lines[i].strip()[start_idx:].strip()
                                # Extract number from duration string
                                import re

                                duration_match = re.search(r"(\d+)", duration_str)
                                if duration_match:
                                    phase["duration_weeks"] = int(
                                        duration_match.group(1)
                                    )
                            elif lines[i].strip().startswith("**Objectives:**"):
                                start_idx = (
                                    lines[i].strip().find("**Objectives:**") + 15
                                )
                                phase["objectives"] = (
                                    lines[i].strip()[start_idx:].strip()
                                )
                            i += 1

                        phases.append(phase)
                        continue

            i += 1

        # Create study plan
        study_plan = StudyPlan(
            title=title,
            description=description,
            phases=phases,
            content_metadata=json.dumps({}),
            is_public=False,
            creator_id=user.id,
        )

        with self.db.get_session() as session:
            session.add(study_plan)
            session.commit()
            # Get the title before the session closes to avoid detached instance issues
            study_plan_title = study_plan.title

        self.logger.info(
            f"Study plan imported from Markdown: {study_plan_title} by {user.username}"
        )
        return study_plan

    def export_bulk_data(
        self,
        user: User,
        include_study_plans: bool = True,
        include_assessments: bool = True,
        include_content: bool = True,
        include_analytics: bool = False,
        format: str = "json",
    ) -> str:
        """
        Export all user data in bulk.

        Args:
            user: User whose data to export
            include_study_plans: Include study plans
            include_assessments: Include assessments
            include_content: Include content
            include_analytics: Include analytics data (sessions, submissions, audit logs)
            format: Export format (json, zip)

        Returns:
            Path to exported file
        """
        role_obj = getattr(user, "role", None)
        role_value = (
            role_obj.value
            if role_obj is not None and getattr(role_obj, "value", None) is not None
            else str(role_obj)
        )
        user_created_at = getattr(user, "created_at", None)

        data: Dict[str, Any] = {
            "schema_version": self.current_schema_version,
            "export_date": datetime.now().isoformat(),
            "user": {
                "username": getattr(user, "username", None) or "",
                "full_name": getattr(user, "full_name", None) or "",
                "role": role_value,
                "created_at": user_created_at.isoformat() if user_created_at else None,
            },
        }

        if include_study_plans:
            with self.db.get_session() as session:
                study_plans = (
                    session.query(StudyPlan).filter_by(creator_id=user.id).all()
                )
                data["study_plans"] = []
                for study_plan in study_plans:
                    plan_data = self.export_study_plan_json(
                        study_plan, include_content, include_assessments
                    )
                    data["study_plans"].append(plan_data)

        if include_assessments:
            with self.db.get_session() as session:
                assessments = (
                    session.query(Assessment).filter_by(created_by_id=user.id).all()
                )
                data["assessments"] = []
                for assessment in assessments:
                    assessment_data = self.export_assessment_json(
                        assessment, include_questions=True
                    )
                    data["assessments"].append(assessment_data)

        # Include analytics data
        if include_analytics:
            with self.db.get_session() as session:
                user_id = user.id

                # Learning sessions analytics
                learning_sessions = (
                    session.query(LearningSession).filter_by(student_id=user_id).all()
                )
                data["analytics"] = {
                    "learning_sessions": [],
                    "assessment_submissions": [],
                    "audit_logs": [],
                    "auth_attempts": [],
                }

                for learning_session in learning_sessions:
                    started_at = (
                        learning_session.start_time.isoformat()
                        if learning_session.start_time
                        else None
                    )
                    completed_at = (
                        learning_session.end_time.isoformat()
                        if learning_session.end_time
                        else None
                    )
                    duration_minutes: Optional[int] = learning_session.duration_minutes
                    if duration_minutes is None:
                        try:
                            duration_minutes = learning_session.calculate_duration()
                        except Exception:
                            duration_minutes = None
                    session_status = getattr(learning_session, "status", None)
                    session_status_value = getattr(session_status, "value", None)

                    session_data = {
                        "id": learning_session.id,
                        "content_id": learning_session.content_id,
                        "status": (
                            session_status_value
                            if session_status_value is not None
                            else str(session_status)
                        ),
                        "score": learning_session.score,
                        "completion_status": learning_session.completion_status,
                        "duration_minutes": duration_minutes,
                        "started_at": started_at,
                        "completed_at": completed_at,
                    }
                    data["analytics"]["learning_sessions"].append(session_data)

                # Assessment submissions analytics
                submissions = (
                    session.query(AssessmentSubmission)
                    .filter_by(student_id=user_id)
                    .all()
                )
                for submission in submissions:
                    percentage: Optional[float] = None
                    if submission.score is not None and submission.total_points:
                        percentage = (
                            submission.score / submission.total_points
                        ) * 100.0

                    passing_score: Optional[int] = None
                    submission_assessment = session.get(
                        Assessment, submission.assessment_id
                    )
                    if submission_assessment is not None:
                        passing_score = submission_assessment.passing_score

                    passed: Optional[bool] = None
                    if percentage is not None and passing_score is not None:
                        passed = percentage >= float(passing_score)

                    submission_data = {
                        "id": submission.id,
                        "assessment_id": submission.assessment_id,
                        "score": submission.score,
                        "total_points": submission.total_points,
                        "percentage": percentage,
                        "passed": passed,
                        "attempt_number": 1,
                        "started_at": (
                            submission.started_at.isoformat()
                            if submission.started_at
                            else None
                        ),
                        "submitted_at": (
                            submission.submitted_at.isoformat()
                            if submission.submitted_at
                            else None
                        ),
                        "graded_at": (
                            submission.graded_at.isoformat()
                            if submission.graded_at
                            else None
                        ),
                        "created_at": (
                            submission.created_at.isoformat()
                            if submission.created_at
                            else None
                        ),
                    }
                    data["analytics"]["assessment_submissions"].append(submission_data)

                # Audit logs analytics
                try:
                    audit_logs = (
                        session.query(AuditLog).filter_by(user_id=user_id).all()
                    )
                    for log in audit_logs:
                        try:
                            event_type_obj = getattr(log, "event_type", None)
                            event_type_value = (
                                event_type_obj.value
                                if event_type_obj is not None
                                and getattr(event_type_obj, "value", None) is not None
                                else str(event_type_obj)
                            )
                            log_timestamp = getattr(log, "timestamp", None)
                            log_data = {
                                "id": log.id,
                                "event_type": event_type_value,
                                "details": log.details,
                                "ip_address": log.ip_address,
                                "user_agent": log.user_agent,
                                "timestamp": (
                                    log_timestamp.isoformat() if log_timestamp else None
                                ),
                            }
                            data["analytics"]["audit_logs"].append(log_data)
                        except Exception as log_error:
                            # Skip invalid audit log entries but log the error
                            self.logger.warning(
                                f"Failed to process audit log {log.id}: {log_error}"
                            )
                            continue
                except Exception as e:
                    # Log audit log processing errors for debugging
                    self.logger.warning(
                        f"Failed to export audit logs for user {user_id}: {e}"
                    )

                # Authentication attempts analytics
                auth_attempts = (
                    session.query(AuthAttempt).filter_by(user_id=user_id).all()
                )
                for attempt in auth_attempts:
                    attempt_timestamp = getattr(attempt, "timestamp", None)
                    attempt_data = {
                        "id": attempt.id,
                        "username": attempt.username,
                        "ip_address": attempt.ip_address,
                        "success": attempt.success,
                        "timestamp": (
                            attempt_timestamp.isoformat() if attempt_timestamp else None
                        ),
                    }
                    data["analytics"]["auth_attempts"].append(attempt_data)

        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = user.username
        filename = f"slmeducator_export_{username}_{timestamp}.{format}"

        if format == "json":
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format == "zip":
            # Create ZIP with JSON and separate files
            with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Main JSON data
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                zipf.writestr("data.json", json_str.encode("utf-8"))

                # Individual files for large content
                if include_study_plans and "study_plans" in data:
                    for i, plan in enumerate(data["study_plans"]):
                        plan_json = json.dumps(plan, indent=2, ensure_ascii=False)
                        zipf.writestr(
                            f"study_plans/plan_{i + 1}.json", plan_json.encode("utf-8")
                        )

        self.logger.info(f"Bulk export completed: {filename}")
        return filename

    def _validate_schema_version(self, version: str) -> None:
        """Validate schema version compatibility."""
        try:
            major_version = float(version.split(".")[0])
            current_major = float(self.current_schema_version.split(".")[0])

            if major_version > current_major:
                raise ValidationError(
                    f"Schema version {version} is newer than supported version "
                    f"{self.current_schema_version}"
                )

        except (ValueError, IndexError):
            raise ValidationError(f"Invalid schema version format: {version}")

    def _import_assessment_json(
        self, data: Dict[str, Any], study_plan_id: int, user: User
    ) -> Assessment:
        """Import assessment from JSON data."""
        assessment_data = data.get("assessment", {})

        assessment = Assessment(
            title=assessment_data.get("title", "Imported Assessment"),
            description=assessment_data.get("description", ""),
            instructions=assessment_data.get("instructions", ""),
            time_limit_minutes=assessment_data.get("time_limit_minutes"),
            max_attempts=assessment_data.get("max_attempts", 1),
            passing_score=assessment_data.get("passing_score", 70),
            total_points=assessment_data.get("total_points", 100),
            is_published=False,  # Imported assessments are unpublished by default
            created_by_id=user.id,
            study_plan_id=study_plan_id,
        )

        with self.db.get_session() as session:
            session.add(assessment)
            session.flush()  # Get ID for questions

            # Import questions
            if "questions" in data:
                for question_data in data["questions"]:
                    try:
                        question = AssessmentQuestion(
                            assessment_id=assessment.id,
                            question_text=question_data.get(
                                "question_text", "Question"
                            ),
                            question_type=QuestionType(
                                question_data.get("question_type", "multiple_choice")
                            ),
                            points=question_data.get("points", 10),
                            order_index=question_data.get("order_index", 0),
                            options=question_data.get("options", []),
                            content_metadata=question_data.get("content_metadata", {}),
                        )
                        # Don't import correct answer for security
                        session.add(question)
                    except Exception as e:
                        self.logger.warning(f"Failed to import question: {e}")
                        continue

        return assessment
