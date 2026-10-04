"""Synthetic progress evidence, source graph scope and durable reward behavior."""

from datetime import timedelta

import pytest

from src.core.models import (
    Badge,
    Content,
    ContentType,
    LearningSession,
    MasteryNode,
    SessionStatus,
    StudyPlan,
    StudyPlanContent,
    StudentStudyPlan,
    User,
    UserBadge,
)
from src.core.services.progress_tracking_service import ProgressTrackingService
from src.core.services.temporal_service import utc_now


@pytest.fixture
def progress_world(db_service, test_teacher, test_student):
    db = db_service.session
    plans = [
        StudyPlan(
            title=f"Synthetic course {i}",
            creator_id=test_teacher.id,
            phases=[{"lessons": ["stale outline"] * 3}],
        )
        for i in range(2)
    ]
    db.add_all(plans)
    db.flush()
    contents = []
    for i, plan in enumerate(plans):
        content = Content(
            title=f"Lesson {i}", content_type=ContentType.LESSON, creator_id=test_teacher.id
        )
        content.set_encrypted_content_data({"content": "Synthetic lesson"})
        db.add(content)
        db.flush()
        db.add(
            StudyPlanContent(
                study_plan_id=plan.id, content_id=content.id, phase_index=0, order_index=0
            )
        )
        contents.append(content)
    db.add(StudentStudyPlan(study_plan_id=plans[0].id, student_id=test_student.id, progress={}))
    db.commit()
    return db, test_student, plans, contents, ProgressTrackingService()


def test_course_progress_uses_its_graph_and_never_other_course_mastery(progress_world):
    db, user, plans, contents, service = progress_world
    assert service.update_mastery(user.id, contents[1].id, 100)
    progress = service.get_study_plan_progress(user.id, plans[0].id)
    assert progress["total_items"] == 1
    assert progress["lessons_completed"] == 0 and progress["completion_pct"] == 0
    assert service.update_mastery(user.id, contents[0].id, 90)
    assert service.get_study_plan_progress(user.id, plans[0].id)["lessons_completed"] == 0
    assignment = db.get(StudentStudyPlan, (user.id, plans[0].id))
    assignment.progress = {"completed_content_ids": [contents[0].id, contents[1].id]}
    db.commit()
    progress = service.get_study_plan_progress(user.id, plans[0].id)
    assert progress["lessons_completed"] == 1 and progress["completion_pct"] == 100
    assert service.get_study_plan_progress(user.id, plans[1].id)["status"] == "not_started"


@pytest.mark.parametrize("level,expected", [(-5, 0), (0, 0), (49.6, 50), (101, 100)])
def test_mastery_clamps_and_updates_existing_node(progress_world, level, expected):
    db, user, plans, contents, service = progress_world
    assert service.get_topic_mastery(user.id, contents[0].id) == 0
    assert service.update_progress(user.id, contents[0].id, level)
    assert service.get_topic_mastery(user.id, contents[0].id) == expected
    assert service.update_progress(user.id, contents[0].id, 70)
    assert service.get_topic_mastery(user.id, contents[0].id) == 70
    assert (
        db.query(MasteryNode).filter_by(student_id=user.id, content_id=contents[0].id).count() == 1
    )


def test_invalid_mastery_has_no_partial_write(progress_world):
    db, user, plans, contents, service = progress_world
    assert not service.update_mastery(user.id, contents[0].id, float("nan"))
    assert db.query(MasteryNode).count() == 0


def test_participation_stats_only_count_known_durations(progress_world):
    db, user, plans, contents, service = progress_world
    now = utc_now()
    db.add_all(
        [
            LearningSession(
                student_id=user.id,
                content_id=contents[0].id,
                status=SessionStatus.COMPLETED,
                start_time=now - timedelta(hours=1),
                end_time=now,
                duration_minutes=60,
            ),
            LearningSession(
                student_id=user.id,
                content_id=contents[0].id,
                status=SessionStatus.COMPLETED,
                start_time=now.replace(tzinfo=None) - timedelta(hours=2),
                end_time=now.replace(tzinfo=None),
                duration_minutes=120,
            ),
        ]
    )
    db.commit()
    service.update_mastery(user.id, contents[0].id, 90)
    assert service.get_student_stats(user.id) == {"total_sessions": 2, "average_mastery": 90.0}
    overall = service.get_overall_progress(user.id)
    assert overall["total_time_hours"] == 1.0 and overall["total_study_plans"] == 1
    assert overall["topics_mastered"] == 1


def test_badges_are_awarded_once_and_inactive_criteria_do_not_count(progress_world):
    db, user, plans, contents, service = progress_world
    db.query(Badge).update({Badge.is_active: False})
    user.xp, user.level = 1000, 2
    db.add_all(
        [
            Badge(
                name="Synthetic XP",
                description="Participation only",
                xp_value=20,
                criteria_type="xp_threshold",
                criteria_value={"threshold": 1000},
            ),
            Badge(
                name="Synthetic level",
                description="Participation only",
                xp_value=0,
                criteria_type="level",
                criteria_value={"level": 2},
            ),
            Badge(
                name="Inactive",
                description="No award",
                xp_value=100,
                is_active=False,
                criteria_type="xp_threshold",
                criteria_value={"threshold": 0},
            ),
            Badge(
                name="Unknown rule",
                description="No award",
                xp_value=100,
                criteria_type="unknown",
                criteria_value={},
            ),
        ]
    )
    db.commit()
    assert len(service.check_and_award_badges(user.id)) == 2
    assert service.check_and_award_badges(user.id) == []
    db.expire_all()
    assert db.get(User, user.id).xp == 1020
    assert db.query(UserBadge).filter_by(user_id=user.id).count() == 2


def test_streak_recording_is_idempotent_per_known_day(progress_world):
    db, user, plans, contents, service = progress_world
    assert service.update_streak(user.id)["current_streak"] == 1
    assert service.update_streak(user.id)["current_streak"] == 1
    assert service.get_streak(user.id)["current_streak"] == 1


def test_missing_user_operations_have_no_rewards(progress_world):
    db, user, plans, contents, service = progress_world
    assert service.award_xp(999999, 50) == {"new_xp": 0, "new_level": 1, "leveled_up": False}
    assert service.check_and_award_badges(999999) == []
    assert service.update_streak(999999) == {"current_streak": 0, "longest_streak": 0}


def test_participation_xp_reports_level_crossing(progress_world):
    db, user, plans, contents, service = progress_world
    user.xp, user.level = 990, 1
    db.commit()
    assert service.award_xp(user.id, 20) == {"new_xp": 1010, "new_level": 2, "leveled_up": True}
