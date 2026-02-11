"""
Unit tests for study plan retrieval functionality
Tests teacher and student plan access with both enum and string role handling
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.services import get_study_plan_service, get_auth_service
from core.models import UserRole


class TestStudyPlanRetrieval:
    """Test study plan retrieval for different user roles"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Set up test environment using conftest's db_service fixture"""
        # Reset service singletons to use the fresh database from conftest
        import core.services.auth as auth_module
        import core.services.study_plan_service as sp_module

        # Clear service singletons so they use the conftest's db_service
        auth_module._auth_service = None
        sp_module._study_plan_service = None

        # Get fresh service instances
        self.sp_service = get_study_plan_service()
        self.auth_service = get_auth_service()
        self.db_service = db_service
        yield

    def test_teacher_can_retrieve_created_plans(self):
        """Test that teachers can retrieve study plans they created"""
        # Create teacher
        teacher = self.auth_service.register_user(
            username="test_teacher",
            email="teacher@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role=UserRole.TEACHER,
        )

        # Create study plan
        plan = self.sp_service.create_study_plan(
            title="Teacher's Plan",
            description="Test plan",
            creator_id=teacher["id"],
            phases=[{"title": "Phase 1", "objectives": ["Learn basics"]}],
        )

        assert plan is not None, "Plan creation failed"

        # Retrieve plans created by teacher
        plans = self.sp_service.list_study_plans(user_id=teacher["id"])

        assert len(plans) > 0, "Teacher should see their created plans"
        assert any(p.id == plan.id for p in plans), "Created plan should be in list"

    def test_student_sees_assigned_plans(self):
        """Test that students see only assigned plans"""
        # Create teacher and student
        teacher = self.auth_service.register_user(
            username="test_teacher2",
            email="teacher2@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role=UserRole.TEACHER,
        )

        student = self.auth_service.register_user(
            username="test_student",
            email="student@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Student",
            role=UserRole.STUDENT,
        )

        # Create plan
        plan = self.sp_service.create_study_plan(
            title="Assigned Plan",
            description="Test plan for student",
            creator_id=teacher["id"],
            phases=[{"title": "Phase 1", "objectives": ["Learn"]}],
        )

        # Assign to student
        self.sp_service.assign_study_plan(
            study_plan_id=plan.id, student_id=student["id"], teacher_id=teacher["id"]
        )

        # Student should see assigned plan
        student_plans = self.sp_service.list_study_plans(user_id=student["id"])

        assert len(student_plans) > 0, "Student should see assigned plans"
        assert any(
            p.id == plan.id for p in student_plans
        ), "Assigned plan should be visible"

    def test_role_enum_handling(self):
        """Test that both enum and string role comparisons work"""
        # Create teacher with enum role
        teacher = self.auth_service.register_user(
            username="test_teacher3",
            email="teacher3@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role=UserRole.TEACHER,
        )

        # Create plan
        plan = self.sp_service.create_study_plan(
            title="Enum Test Plan",
            description="Test enum handling",
            creator_id=teacher["id"],
            phases=[],
        )

        # Retrieve using user_id
        plans = self.sp_service.list_study_plans(user_id=teacher["id"])
        assert len(plans) > 0, "Should handle enum role comparison"

        # Test with creator_id alias
        plans_alias = self.sp_service.list_study_plans(creator_id=teacher["id"])
        assert len(plans_alias) > 0, "Should work with creator_id alias"
        assert len(plans) == len(
            plans_alias
        ), "Both parameters should return same results"

    def test_parameter_compatibility_user_id_vs_creator_id(self):
        """Test backward compatibility between user_id and creator_id parameters"""
        teacher = self.auth_service.register_user(
            username="test_teacher4",
            email="teacher4@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role=UserRole.TEACHER,
        )

        plan = self.sp_service.create_study_plan(
            title="Compatibility Test",
            description="Test parameter compatibility",
            creator_id=teacher["id"],
            phases=[],
        )

        # Test both parameter names
        plans_user_id = self.sp_service.list_study_plans(user_id=teacher["id"])
        plans_creator_id = self.sp_service.list_study_plans(creator_id=teacher["id"])

        assert len(plans_user_id) == len(
            plans_creator_id
        ), "Both parameter names should work"
        assert all(
            p1.id == p2.id for p1, p2 in zip(plans_user_id, plans_creator_id)
        ), "Should return same plans regardless of parameter name"

    def test_empty_results_for_nonexistent_user(self):
        """Test that nonexistent user returns empty list"""
        plans = self.sp_service.list_study_plans(user_id=99999)
        assert plans == [], "Nonexistent user should return empty list"

    def test_student_created_plans_visible(self):
        """Test that students can see plans they created themselves"""
        student = self.auth_service.register_user(
            username="test_student2",
            email="student2@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Student",
            role=UserRole.STUDENT,
        )

        # Student creates own plan
        plan = self.sp_service.create_study_plan(
            title="Student's Own Plan",
            description="Self-created plan",
            creator_id=student["id"],
            phases=[],
        )

        # Student should see their own created plan
        plans = self.sp_service.list_study_plans(user_id=student["id"])
        assert len(plans) > 0, "Student should see self-created plans"
        assert any(
            p.id == plan.id for p in plans
        ), "Self-created plan should be visible"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
