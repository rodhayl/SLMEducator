"""
SQLAlchemy models for SLMEducator

This module contains all database models as specified in the requirements document.
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    Index,
    Date,
    Float,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON
from cryptography.fernet import Fernet
import json

Base = declarative_base()

# Encryption setup - use persistent key from security_utils
from ..security_utils import get_or_create_encryption_key

ENCRYPTION_KEY = get_or_create_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)


class UserRole(enum.Enum):
    """User roles as specified in requirements"""

    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"


class ContentType(enum.Enum):
    """Content types for polymorphic content"""

    LESSON = "lesson"
    EXERCISE = "exercise"
    ASSESSMENT = "assessment"
    QA = "qa"


class SessionStatus(enum.Enum):
    """Learning session statuses"""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(enum.Enum):
    """Audit event types"""

    AUTH = "auth"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"


class QuestionType(enum.Enum):
    """Assessment question types"""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    FILL_IN_BLANK = "fill_in_blank"


class SubmissionStatus(enum.Enum):
    """Assessment submission statuses"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    AI_GRADED = "ai_graded"  # AI graded, pending teacher review
    GRADED = "graded"  # Final grade (teacher approved or AI auto)
    RETURNED = "returned"


class GradingMode(enum.Enum):
    """Assessment grading modes"""

    AI_AUTOMATIC = "ai_automatic"  # AI grades instantly, no review needed
    AI_ASSISTED = "ai_assisted"  # AI suggests grades, teacher reviews
    MANUAL = "manual"  # Teacher grades all subjective questions


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    if not data:
        return data
    return cipher.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    if not encrypted_data:
        return encrypted_data
    try:
        return cipher.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return encrypted_data  # Return as-is if decryption fails


class User(Base):
    """User entity as specified in ENT-001"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    grade_level = Column(String(50), nullable=True)  # For students
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Phase 3: Gamification fields

    xp = Column(Integer, default=0, nullable=False)

    level = Column(Integer, default=1, nullable=False)

    current_streak = Column(Integer, default=0, nullable=False)

    longest_streak = Column(Integer, default=0, nullable=False)

    last_activity_date = Column(Date, nullable=True)

    # Relationships
    teacher = relationship("User", remote_side=[id], backref="students")
    created_study_plans = relationship("StudyPlan", back_populates="creator")
    learning_sessions = relationship("LearningSession", back_populates="student")
    sent_messages = relationship(
        "TeacherMessage", foreign_keys="TeacherMessage.from_id", back_populates="sender"
    )
    received_messages = relationship(
        "TeacherMessage",
        foreign_keys="TeacherMessage.to_id",
        back_populates="recipient",
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    auth_attempts = relationship("AuthAttempt", back_populates="user")
    student_assignments = relationship(
        "StudentStudyPlan",
        foreign_keys="StudentStudyPlan.student_id",
        back_populates="student",
    )
    created_assessments = relationship("Assessment", back_populates="created_by")
    assessment_submissions = relationship(
        "AssessmentSubmission", back_populates="student"
    )
    created_rubrics = relationship("Rubric", back_populates="created_by")
    logging_config = relationship("LoggingConfiguration", back_populates="user")
    application_config = relationship("ApplicationConfiguration", back_populates="user")

    # Generic settings storage (e.g. for student notes)
    settings = Column(JSON, nullable=True, default=dict)

    def __repr__(self):
        return (
            f"<User(id={self.id}, username='{self.username}', role={self.role.value})>"
        )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudyPlan(Base):
    """StudyPlan entity as specified in ENT-002"""

    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    phases = Column(JSON, nullable=False, default=list)  # JSON structure as specified
    content_metadata = Column(Text, nullable=True)  # Encrypted JSON
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    creator = relationship("User", back_populates="created_study_plans")
    contents = relationship("Content", back_populates="study_plan")
    books = relationship("Book", back_populates="study_plan")
    student_assignments = relationship("StudentStudyPlan", back_populates="study_plan")
    assessments = relationship("Assessment", back_populates="study_plan")
    plan_contents = relationship(
        "StudyPlanContent", back_populates="study_plan", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StudyPlan(id={self.id}, title='{self.title}')>"

    @property
    def decrypted_metadata(self) -> Optional[Dict[str, Any]]:
        """Get decrypted metadata"""
        if self.content_metadata:
            try:
                decrypted = decrypt_data(self.content_metadata)
                return json.loads(decrypted) if decrypted else None
            except Exception:
                return None
        return None

    def set_encrypted_metadata(self, metadata: Dict[str, Any]):
        """Set encrypted metadata"""
        if metadata:
            json_str = json.dumps(metadata)
            self.content_metadata = encrypt_data(json_str)
        else:
            self.content_metadata = None


class StudyPlanContent(Base):
    """Association table for StudyPlan content items (Many-to-Many with metadata)"""

    __tablename__ = "study_plan_contents"

    id = Column(Integer, primary_key=True)
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), nullable=False, index=True
    )
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    phase_index = Column(Integer, nullable=False, default=0)
    order_index = Column(Integer, nullable=False, default=0)
    is_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="plan_contents")
    content = relationship("Content", back_populates="plan_associations")

    def __repr__(self):
        return f"<StudyPlanContent(plan={self.study_plan_id}, content={self.content_id}, phase={self.phase_index})>"


class Content(Base):
    """Content entity as specified in ENT-003"""

    __tablename__ = "contents"

    id = Column(Integer, primary_key=True)
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), nullable=True, index=True
    )
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    content_type = Column(SQLEnum(ContentType), nullable=False)
    title = Column(String(200), nullable=False)
    content_data = Column(Text, nullable=True)  # Encrypted JSON or text
    difficulty = Column(Integer, default=1, nullable=False)
    estimated_time_min = Column(Integer, default=15, nullable=False)
    is_personal = Column(Boolean, default=False, nullable=False)
    shared_with_teacher = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Phase 1: Adaptive AI Tutor fields
    verification_required = Column(
        Boolean, default=False, nullable=False
    )  # Requires Socratic checkpoint
    remedial_for_content_id = Column(
        Integer, ForeignKey("contents.id"), nullable=True
    )  # Remedial content link
    difficulty_prerequisites = Column(
        JSON, nullable=True, default=list
    )  # List of prerequisite content IDs

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="contents")
    creator = relationship("User", foreign_keys=[creator_id], backref="created_content")
    plan_associations = relationship(
        "StudyPlanContent", back_populates="content", cascade="all, delete-orphan"
    )
    learning_sessions = relationship("LearningSession", back_populates="content")
    assessments = relationship("Assessment", back_populates="topic")

    def __repr__(self):
        return f"<Content(id={self.id}, title='{self.title}', type={self.content_type.value})>"

    @property
    def decrypted_content_data(self) -> Optional[Dict[str, Any]]:
        """Get decrypted content data"""
        if self.content_data:
            try:
                decrypted = decrypt_data(self.content_data)
                return json.loads(decrypted) if decrypted else None
            except Exception:
                return None
        return None

    def set_encrypted_content_data(self, data: Dict[str, Any]):
        """Set encrypted content data"""
        if data:
            json_str = json.dumps(data)
            self.content_data = encrypt_data(json_str)
        else:
            self.content_data = None


class Book(Base):
    """Book entity as specified in ENT-004"""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    chapters = Column(JSON, nullable=False, default=list)  # List of topic_ids
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="books")

    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}')>"


class StudentStudyPlan(Base):
    """StudentStudyPlan entity as specified in ENT-005 (Assignment)"""

    __tablename__ = "student_study_plans"

    student_id = Column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), primary_key=True, index=True
    )
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    progress = Column(
        JSON, nullable=False, default=dict
    )  # {completed: int, score: float}
    completed_at = Column(DateTime, nullable=True)

    # Phase 1: Adaptive AI Tutor fields
    mastery_graph = Column(
        JSON, nullable=True, default=dict
    )  # Graph of content mastery relationships
    forgetting_curve_data = Column(
        JSON, nullable=True, default=dict
    )  # Forgetting curve patterns

    # Relationships
    student = relationship("User", back_populates="student_assignments")
    study_plan = relationship("StudyPlan", back_populates="student_assignments")

    def __repr__(self):
        return f"<StudentStudyPlan(student_id={self.student_id}, study_plan_id={self.study_plan_id})>"

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.progress:
            return self.progress.get("score", 0.0)
        return 0.0


class LearningSession(Base):
    """LearningSession entity as specified in ENT-006"""

    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True, index=True)
    start_time = Column(DateTime, default=func.now(), nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(
        SQLEnum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE, index=True
    )
    score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    completion_status = Column(String(50), nullable=True)  # Additional status field
    duration_minutes = Column(Integer, nullable=True)  # Calculated duration

    # Relationships
    student = relationship("User", back_populates="learning_sessions")
    content = relationship("Content", back_populates="learning_sessions")

    def __repr__(self):
        return f"<LearningSession(id={self.id}, student_id={self.student_id}, status={self.status.value})>"

    def calculate_duration(self):
        """Calculate session duration in minutes"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return None


class AIModelConfiguration(Base):
    """AIModelConfiguration entity as specified in ENT-007"""

    __tablename__ = "ai_model_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # ollama/openai/lm_studio/anthropic
    model = Column(String(100), nullable=False)
    endpoint = Column(String(500), nullable=True)
    api_key = Column(Text, nullable=True)  # Encrypted
    validated = Column(Boolean, default=False, nullable=False)
    model_parameters = Column(JSON, nullable=True)  # temperature, max_tokens, etc.
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AIModelConfiguration(id={self.id}, provider='{self.provider}', model='{self.model}')>"

    @property
    def decrypted_api_key(self) -> Optional[str]:
        """Get decrypted API key"""
        if self.api_key:
            try:
                return decrypt_data(self.api_key)
            except Exception:
                return None
        return None

    def set_encrypted_api_key(self, api_key: str):
        """Set encrypted API key"""
        if api_key:
            self.api_key = encrypt_data(api_key)
        else:
            self.api_key = None


class TeacherMessage(Base):
    """TeacherMessage entity as specified in ENT-008"""

    __tablename__ = "teacher_messages"

    id = Column(Integer, primary_key=True)
    from_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=func.now(), nullable=False)
    read_at = Column(DateTime, nullable=True, index=True)
    archived_at = Column(DateTime, nullable=True, index=True)  # NEW: Archive support

    # Relationships
    sender = relationship(
        "User", foreign_keys=[from_id], back_populates="sent_messages"
    )
    recipient = relationship(
        "User", foreign_keys=[to_id], back_populates="received_messages"
    )

    def __repr__(self):
        return f"<TeacherMessage(id={self.id}, from_id={self.from_id}, to_id={self.to_id})>"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_as_read(self):
        """Mark message as read"""
        if not self.read_at:
            self.read_at = datetime.now()


class AuditLog(Base):
    """AuditLog entity as specified in ENT-009"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    details = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type.value}, user_id={self.user_id})>"

    @classmethod
    def log_event(
        cls,
        event_type: EventType,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Helper method to log audit events"""
        return cls(
            user_id=user_id,
            event_type=event_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )


class AuthAttempt(Base):
    """Authentication attempt tracking for rate limiting and account lockout"""

    __tablename__ = "auth_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    success = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="auth_attempts")

    def __repr__(self):
        return f"<AuthAttempt(id={self.id}, username={self.username}, success={self.success})>"

    @classmethod
    def record_attempt(
        cls,
        username: str,
        success: bool,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ):
        """Record an authentication attempt"""
        return cls(
            user_id=user_id, username=username, ip_address=ip_address, success=success
        )


class Assessment(Base):
    """Assessment entity for storing assessment metadata"""

    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    max_attempts = Column(Integer, default=1, nullable=False)
    passing_score = Column(Integer, default=70, nullable=False)
    total_points = Column(Integer, default=100, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), nullable=True, index=True
    )
    topic_id = Column(Integer, ForeignKey("contents.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Grading configuration
    grading_mode = Column(
        SQLEnum(GradingMode), default=GradingMode.AI_ASSISTED, nullable=False
    )

    # Relationships
    created_by = relationship("User", back_populates="created_assessments")
    study_plan = relationship("StudyPlan", back_populates="assessments")
    topic = relationship("Content", back_populates="assessments")
    questions = relationship(
        "AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan"
    )
    submissions = relationship(
        "AssessmentSubmission",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    rubrics = relationship(
        "Rubric", back_populates="assessment", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Assessment(id={self.id}, title='{self.title}', published={self.is_published})>"


class AssessmentQuestion(Base):
    """Assessment question entity"""

    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False, index=True)
    points = Column(Integer, default=10, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    correct_answer = Column(Text, nullable=True)  # Encrypted for security
    options = Column(JSON, nullable=True)  # For multiple choice, true/false
    content_metadata = Column(JSON, nullable=True)  # Rubrics, hints, explanations
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    responses = relationship(
        "QuestionResponse", back_populates="question", cascade="all, delete-orphan"
    )
    rubrics = relationship(
        "Rubric", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AssessmentQuestion(id={self.id}, type={self.question_type.value}, points={self.points})>"

    def get_decrypted_correct_answer(self) -> Optional[str]:
        """Get decrypted correct answer"""
        if self.correct_answer:
            try:
                return decrypt_data(self.correct_answer)
            except Exception:
                return None
        return None

    def set_encrypted_correct_answer(self, answer: str):
        """Set encrypted correct answer"""
        if answer:
            self.correct_answer = encrypt_data(answer)
        else:
            self.correct_answer = None


class AssessmentSubmission(Base):
    """Student assessment submission"""

    __tablename__ = "assessment_submissions"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id"), nullable=False, index=True
    )
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        SQLEnum(SubmissionStatus),
        default=SubmissionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    score = Column(Integer, nullable=True)
    total_points = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    submitted_at = Column(DateTime, nullable=True, index=True)
    graded_at = Column(DateTime, nullable=True)
    time_spent_minutes = Column(Integer, default=0, nullable=False)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Phase 2: Connected Classroom - AI-assisted grading fields
    ai_draft_feedback = Column(Text, nullable=True)  # AI-generated feedback draft
    ai_draft_score = Column(Integer, nullable=True)  # AI-suggested score
    teacher_approved = Column(
        Boolean, default=False, nullable=False
    )  # Teacher approval flag

    # Relationships
    assessment = relationship("Assessment", back_populates="submissions")
    student = relationship("User", back_populates="assessment_submissions")
    responses = relationship(
        "QuestionResponse", back_populates="submission", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AssessmentSubmission(id={self.id}, status={self.status.value}, score={self.score})>"

    def calculate_score(self) -> int:
        """Calculate total score from responses"""
        total_score = 0
        for response in self.responses:
            if response.score is not None:
                total_score += response.score
        return total_score

    def is_passing(self) -> bool:
        """Check if submission meets passing criteria"""
        if self.score is None or self.assessment.passing_score is None:
            return False
        return self.score >= self.assessment.passing_score


class QuestionResponse(Base):
    """Student response to assessment question"""

    __tablename__ = "question_responses"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer, ForeignKey("assessment_submissions.id"), nullable=False, index=True
    )
    question_id = Column(
        Integer, ForeignKey("assessment_questions.id"), nullable=False, index=True
    )
    response_text = Column(Text, nullable=True)  # Encrypted for security
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, default=func.now(), nullable=False)
    graded_at = Column(DateTime, nullable=True)

    # AI grading fields
    ai_suggested_score = Column(Integer, nullable=True)  # AI's suggested score
    ai_suggested_feedback = Column(Text, nullable=True)  # AI's feedback/explanation
    ai_confidence = Column(Float, nullable=True)  # AI confidence 0.0-1.0
    teacher_override = Column(
        Boolean, default=False, nullable=False
    )  # Teacher modified AI grade

    # Relationships
    submission = relationship("AssessmentSubmission", back_populates="responses")
    question = relationship("AssessmentQuestion", back_populates="responses")

    def __repr__(self):
        return f"<QuestionResponse(id={self.id}, score={self.score}, correct={self.is_correct})>"

    def get_decrypted_response(self) -> Optional[str]:
        """Get decrypted response text"""
        if self.response_text:
            try:
                return decrypt_data(self.response_text)
            except Exception:
                return None
        return None

    def set_encrypted_response(self, response: str):
        """Set encrypted response text"""
        if response:
            self.response_text = encrypt_data(response)
        else:
            self.response_text = None


class Rubric(Base):
    """Rubric for assessment grading"""

    __tablename__ = "rubrics"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    total_points = Column(Integer, default=100, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id"), nullable=True, index=True
    )
    question_id = Column(
        Integer, ForeignKey("assessment_questions.id"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    created_by = relationship("User", back_populates="created_rubrics")
    assessment = relationship("Assessment", back_populates="rubrics")
    question = relationship("AssessmentQuestion", back_populates="rubrics")
    criteria = relationship(
        "RubricCriterion", back_populates="rubric", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Rubric(id={self.id}, name='{self.name}', points={self.total_points})>"


class RubricCriterion(Base):
    """Rubric criterion for detailed grading"""

    __tablename__ = "rubric_criteria"

    id = Column(Integer, primary_key=True)
    rubric_id = Column(Integer, ForeignKey("rubrics.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    max_points = Column(Integer, default=10, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    # Relationships
    rubric = relationship("Rubric", back_populates="criteria")

    def __repr__(self):
        return f"<RubricCriterion(id={self.id}, name='{self.name}', max_points={self.max_points})>"


class LoggingConfiguration(Base):
    """Logging configuration for the application"""

    __tablename__ = "logging_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )  # Null for system-wide config
    level = Column(String(20), default="INFO", nullable=False)
    max_file_size_mb = Column(Integer, default=10, nullable=False)
    backup_count = Column(Integer, default=5, nullable=False)
    log_to_console = Column(Boolean, default=True, nullable=False)
    log_to_file = Column(Boolean, default=True, nullable=False)
    structured_logging = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="logging_config")

    def __repr__(self):
        return f"<LoggingConfiguration(id={self.id}, user_id={self.user_id}, level='{self.level}')>"


class ApplicationConfiguration(Base):
    """Application configuration settings"""

    __tablename__ = "application_configurations"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )  # Null for system-wide config
    theme = Column(String(20), default="auto", nullable=False)
    font_size = Column(String(10), default="medium", nullable=False)
    auto_save = Column(Boolean, default=True, nullable=False)
    cache_size_mb = Column(Integer, default=100, nullable=False)
    language = Column(String(10), default="en", nullable=False)
    date_format = Column(String(20), default="%Y-%m-%d", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    enable_tooltips = Column(Boolean, default=True, nullable=False)
    enable_animations = Column(Boolean, default=True, nullable=False)
    show_welcome_screen = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="application_config")

    def __repr__(self):
        return f"<ApplicationConfiguration(id={self.id}, user_id={self.user_id}, theme='{self.theme}')>"


# ============================================================================
# PHASE 1: ADAPTIVE AI TUTOR MODELS
# ============================================================================


class MasteryNode(Base):
    """Phase 1: Mastery tracking for individual content items with spaced repetition"""

    __tablename__ = "mastery_nodes"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    mastery_level = Column(Integer, default=0, nullable=False)  # 0-100
    last_reviewed = Column(DateTime, nullable=True)
    next_review_due = Column(DateTime, nullable=True, index=True)
    review_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    content = relationship("Content", foreign_keys=[content_id])

    # Composite unique constraint
    __table_args__ = (
        Index("idx_student_content", "student_id", "content_id", unique=True),
    )

    def __repr__(self):
        return f"<MasteryNode(student_id={self.student_id}, content_id={self.content_id}, level={self.mastery_level})>"


# ============================================================================
# PHASE 2: CONNECTED CLASSROOM MODELS
# ============================================================================


class Annotation(Base):
    """Phase 2: Content annotations for teacher-student communication"""

    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text_selection_start = Column(Integer, nullable=True)  # Character offset start
    text_selection_end = Column(Integer, nullable=True)  # Character offset end
    annotation_text = Column(Text, nullable=False)
    annotation_type = Column(
        String(50), nullable=False, default="comment"
    )  # question/comment/highlight
    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    content = relationship("Content", foreign_keys=[content_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Annotation(id={self.id}, type='{self.annotation_type}')>"


class HelpRequest(Base):
    """Phase 2: Student help requests for teacher office hours queue"""

    __tablename__ = "help_requests"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True, index=True)
    question_id = Column(
        Integer, ForeignKey("assessment_questions.id"), nullable=True, index=True
    )
    study_plan_id = Column(
        Integer, ForeignKey("study_plans.id"), nullable=True, index=True
    )
    request_text = Column(Text, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1-5
    status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, in_progress, resolved
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    content = relationship("Content", foreign_keys=[content_id])
    question = relationship("AssessmentQuestion", foreign_keys=[question_id])
    study_plan = relationship("StudyPlan", foreign_keys=[study_plan_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    def __repr__(self):
        return f"<HelpRequest(id={self.id}, student_id={self.student_id}, status='{self.status}')>"


# ============================================================================
# PHASE 3: GAMIFIED MASTERY MODELS
# ============================================================================


class Badge(Base):
    """Phase 3: Badge definitions for gamification"""

    __tablename__ = "badges"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    icon_path = Column(String(255), nullable=True)
    xp_value = Column(Integer, default=0, nullable=False)
    criteria_type = Column(
        String(50), nullable=False
    )  # xp_threshold, streak, content_complete, assessment_score
    criteria_value = Column(JSON, nullable=False)  # Flexible criteria storage
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user_badges = relationship(
        "UserBadge", back_populates="badge", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Badge(id={self.id}, name='{self.name}')>"


class UserBadge(Base):
    """Phase 3: User badge achievements"""

    __tablename__ = "user_badges"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), primary_key=True, index=True)
    earned_at = Column(DateTime, default=func.now(), nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # For partially earned badges

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    badge = relationship("Badge", back_populates="user_badges")

    def __repr__(self):
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id})>"


class DailyGoal(Base):
    """Phase 3: Daily learning goals for students"""

    __tablename__ = "daily_goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_date = Column(Date, nullable=False, index=True)
    goal_type = Column(String(50), nullable=False)  # lessons, exercises, time
    target_value = Column(Integer, nullable=False)
    current_value = Column(Integer, default=0, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Composite unique constraint
    __table_args__ = (Index("idx_user_goal_date", "user_id", "goal_date", unique=True),)

    def __repr__(self):
        return f"<DailyGoal(id={self.id}, user_id={self.user_id}, type='{self.goal_type}')>"


class LeaderboardEntry(Base):
    """Phase 3: Leaderboard rankings"""

    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period = Column(
        String(20), nullable=False, index=True
    )  # daily, weekly, monthly, all_time
    xp = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Composite index for efficient queries
    __table_args__ = (
        Index("idx_period_rank", "period", "rank"),
        Index("idx_user_period", "user_id", "period", unique=True),
    )


class GamificationSettings(Base):
    """Phase 3: User preferences for gamification (e.g., default daily goals)"""

    __tablename__ = "gamification_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    default_goal_type = Column(String(50), nullable=True)
    default_goal_target = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="gamification_settings")

    def __repr__(self):
        return f"<GamificationSettings(user_id={self.user_id}, goal='{self.default_goal_type}')>"
