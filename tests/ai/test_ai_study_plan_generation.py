#!/usr/bin/env python3
"""
Test AI Study Plan Generation - Using Real AI

This test generates an AI study plan for "Logic" using the exact same code path
as the GUI (PlanGenerationWorker), but without GUI dependencies.

It uses the real AI configuration from settings.properties and validates that
the full plan with complete content is created.
"""

import sys
import os
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.services.database import DatabaseService
from src.core.services.ai_service import AIService
from src.core.services.settings_config_service import get_settings_service
from src.core.services.logging import get_logging_service
from src.core.models import User, UserRole, StudyPlan, AIModelConfig


class AIStudyPlanGenerationTest:
    """Test AI study plan generation with real AI integration"""

    def __init__(self):
        self.db_service = None
        self.ai_service = None
        self.test_user = None
        self.logger = get_logging_service().get_logger("test.ai_study_plan_generation")
        self.test_results = []

    def setup_test_environment(self):
        """Set up test environment with database and user"""
        self.logger.info("=" * 60)
        self.logger.info("Setting up test environment...")
        self.logger.info("=" * 60)

        # Initialize database service
        self.db_service = DatabaseService()

        # Create unique test user
        timestamp = int(time.time())
        test_user = User(
            username=f"test_logic_teacher_{timestamp}",
            email=f"test_logic_teacher_{timestamp}@example.com",
            password_hash="test_password_hash",
            first_name="Logic",
            last_name="Teacher",
            role=UserRole.TEACHER,
        )

        self.test_user = self.db_service.create_user(test_user)

        if not self.test_user:
            raise Exception("Failed to create test user")

        self.logger.info(
            f"✓ Created test user: {self.test_user.username} (ID: {self.test_user.id})"
        )

        # Initialize AI service with real configuration (same as PlanGenerationWorker)
        settings = get_settings_service()
        ai_defaults = settings.get_ai_config_defaults()

        self.logger.info(f"✓ Loading AI configuration...")
        self.logger.info(f"  Provider: {ai_defaults.get('default_provider')}")
        self.logger.info(f"  Model: {ai_defaults.get('default_model')}")

        # Configure AI service exactly like PlanGenerationWorker does
        config = AIModelConfig(
            provider=ai_defaults.get("default_provider", "openrouter"),
            model=ai_defaults.get("default_model", "openrouter/sherlock-dash-alpha"),
            api_key=(
                ai_defaults.get("openrouter_api_key")
                if ai_defaults.get("default_provider") == "openrouter"
                else None
            ),
        )

        # Handle OpenAI provider
        if config.provider == "openai":
            config.api_key = settings.get("ai", "openai.api_key")

        self.ai_service = AIService(config, self.logger)

        self.logger.info("✓ AI service initialized with real configuration")
        self.logger.info("Test environment setup complete\n")

    def test_generate_logic_study_plan(self):
        """Generate a study plan for Logic using real AI"""
        self.logger.info("=" * 60)
        self.logger.info("TEST: Generating Logic Study Plan with Real AI")
        self.logger.info("=" * 60)

        try:
            # Define study plan parameters
            subject = "Logic"
            grade_level = "University"
            learning_objectives = [
                "Understand propositional logic and truth tables",
                "Learn predicate logic and quantifiers",
                "Master logical inference and proof techniques",
                "Apply logic to real-world reasoning problems",
            ]
            duration_weeks = 8

            self.logger.info(f"Subject: {subject}")
            self.logger.info(f"Grade Level: {grade_level}")
            self.logger.info(f"Duration: {duration_weeks} weeks")
            self.logger.info(
                f"Learning Objectives: {len(learning_objectives)} objectives"
            )
            self.logger.info("")

            # Generate study plan using real AI (same as PlanGenerationWorker.run())
            self.logger.info("Calling AI service to generate study plan...")
            self.logger.info("(This may take 10-30 seconds depending on AI provider)")
            self.logger.info("")

            plan_data = self.ai_service.generate_study_plan(
                user=self.test_user,
                subject=subject,
                grade_level=grade_level,
                learning_objectives=learning_objectives,
                duration_weeks=duration_weeks,
            )

            self.logger.info("✓ AI service returned plan data")

            # Validate the plan structure
            self._validate_plan_structure(
                plan_data, subject, duration_weeks, learning_objectives
            )

            # Save to database (same as PlanGenerationWorker does)
            self.logger.info("\nSaving study plan to database...")

            study_plan = StudyPlan(
                title=f"Study Plan: {subject}",
                description=plan_data.get(
                    "description", f"A {duration_weeks}-week study plan for {subject}"
                ),
                creator_id=self.test_user.id,
                phases=plan_data if isinstance(plan_data, list) else [plan_data],
                is_public=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            saved_plan = self.db_service.create_study_plan(study_plan)

            if saved_plan:
                self.logger.info(
                    f"✓ Study plan saved to database (ID: {saved_plan.id})"
                )

                # Verify database content
                self._verify_database_content(saved_plan.id)

                self.test_results.append(
                    {
                        "test": "generate_logic_study_plan",
                        "status": "PASSED",
                        "message": f'Successfully generated and saved Logic study plan with {len(plan_data.get("phases", []))} phases',
                    }
                )

                self.logger.info(
                    "\n✅ TEST PASSED: Logic study plan generated successfully with real AI"
                )
            else:
                raise Exception("Failed to save study plan to database")

        except Exception as e:
            self.logger.error(f"\n❌ TEST FAILED: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

            self.test_results.append(
                {
                    "test": "generate_logic_study_plan",
                    "status": "FAILED",
                    "message": str(e),
                }
            )
        finally:
            # Cleanup resources (close AI client and dispose DB connections)
            try:
                if self.ai_service:
                    self.ai_service.close()
            except Exception:
                pass
            try:
                if self.db_service:
                    self.db_service.close()
            except Exception:
                pass

    def _validate_plan_structure(
        self, plan_data, expected_subject, expected_duration, expected_objectives
    ):
        """Validate the structure of the generated plan"""
        self.logger.info("\nValidating plan structure...")

        # Check basic structure
        if not isinstance(plan_data, dict):
            raise Exception(f"Plan data should be dict, got {type(plan_data)}")

        # Check title
        if "title" in plan_data:
            self.logger.info(f"  ✓ Title: {plan_data['title']}")

        # Check description
        if "description" in plan_data:
            self.logger.info(f"  ✓ Description: {plan_data['description'][:80]}...")

        # Check phases
        phases = plan_data.get("phases", [])
        if not phases:
            raise Exception("Plan has no phases")

        self.logger.info(f"  ✓ Phases: {len(phases)}")

        # Validate each phase
        total_topics = 0
        for i, phase in enumerate(phases):
            if not isinstance(phase, dict):
                raise Exception(f"Phase {i} is not a dict")

            phase_title = phase.get("title", f"Phase {i + 1}")
            topics = phase.get("topics", [])

            if not topics:
                raise Exception(f"Phase '{phase_title}' has no topics")

            self.logger.info(
                f"    Phase {i + 1}: '{phase_title}' - {len(topics)} topics"
            )

            # Validate topics
            for j, topic in enumerate(topics):
                if not isinstance(topic, dict):
                    raise Exception(f"Topic {j} in phase '{phase_title}' is not a dict")

                topic_title = topic.get("title")
                if not topic_title:
                    raise Exception(f"Topic {j} in phase '{phase_title}' has no title")

                # Check for key fields
                has_description = "description" in topic
                has_objectives = "learning_objectives" in topic
                has_hours = "estimated_hours" in topic

                self.logger.info(f"      - {topic_title}")
                if has_description:
                    self.logger.info(
                        f"        Description: {topic.get('description', '')[:60]}..."
                    )
                if has_objectives:
                    objectives = topic.get("learning_objectives", [])
                    self.logger.info(f"        Learning objectives: {len(objectives)}")
                if has_hours:
                    self.logger.info(
                        f"        Estimated hours: {topic.get('estimated_hours')}"
                    )

                total_topics += 1

        self.logger.info(f"\n  ✓ Total topics across all phases: {total_topics}")

        if total_topics == 0:
            raise Exception("Plan has no topics")

        self.logger.info("  ✓ Plan structure validation PASSED")

    def _verify_database_content(self, plan_id):
        """Verify the plan was saved correctly to the database"""
        self.logger.info("\nVerifying database content...")

        # Retrieve the plan from database
        with self.db_service.get_session() as session:
            from src.core.models.models import StudyPlan

            saved_plan = session.query(StudyPlan).filter_by(id=plan_id).first()

            if not saved_plan:
                raise Exception(f"Plan {plan_id} not found in database")

            self.logger.info(f"  ✓ Plan found in database")
            self.logger.info(f"  ✓ Title: {saved_plan.title}")
            self.logger.info(f"  ✓ Creator ID: {saved_plan.creator_id}")

            # Check phases
            if isinstance(saved_plan.phases, list):
                self.logger.info(f"  ✓ Phases: {len(saved_plan.phases)}")
            elif isinstance(saved_plan.phases, dict):
                phases = saved_plan.phases.get("phases", [])
                self.logger.info(f"  ✓ Phases: {len(phases)}")

            self.logger.info("  ✓ Database content verification PASSED")

    def cleanup_test_environment(self):
        """Clean up test data"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Cleaning up test environment...")
        self.logger.info("=" * 60)

        try:
            if self.test_user:
                with self.db_service.get_session() as session:
                    # Delete associated study plans
                    from src.core.models.models import StudyPlan

                    plans = (
                        session.query(StudyPlan)
                        .filter_by(creator_id=self.test_user.id)
                        .all()
                    )
                    for plan in plans:
                        session.delete(plan)
                        self.logger.info(f"✓ Deleted study plan: {plan.title}")

                    # Delete test user
                    session.delete(self.test_user)
                    session.commit()

                self.logger.info(f"✓ Deleted test user: {self.test_user.username}")

            self.logger.info("Test environment cleanup complete\n")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("🚀 AI STUDY PLAN GENERATION TEST - REAL AI INTEGRATION")
        print("=" * 60)
        print("")

        try:
            self.setup_test_environment()
            self.test_generate_logic_study_plan()

        except Exception as e:
            self.logger.error(f"Test suite failed: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

        finally:
            self.cleanup_test_environment()

        # Print summary
        self._print_test_summary()

    def _print_test_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        if not self.test_results:
            print("No tests were executed")
            return

        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        total = len(self.test_results)

        print(f"Tests passed: {passed}/{total}")
        if total > 0:
            print(f"Success rate: {passed / total * 100:.1f}%")
        print()

        for result in self.test_results:
            symbol = "✅" if result["status"] == "PASSED" else "❌"
            print(f"{symbol} {result['test']}: {result['message']}")

        print("=" * 60)


def main():
    """Main function"""
    test = AIStudyPlanGenerationTest()
    test.run_all_tests()


if __name__ == "__main__":
    main()
