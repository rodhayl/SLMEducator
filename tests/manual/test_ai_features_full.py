import logging
import sys
import os
from typing import Dict
from dataclasses import dataclass

# Add project root to path
sys.path.append(os.getcwd())

from src.core.services.ai_service import AIService, RuntimeAIConfig
from src.core.models import UserRole

# Mock Models for testing


@dataclass
class MockUser:
    id: int = 1
    username: str = "test_user"
    full_name: str = "Test User"
    grade_level: str = "10th Grade"
    role: UserRole = UserRole.STUDENT


@dataclass
class MockContent:
    id: int = 101
    title: str = "Original Content"
    content_type: str = "text"
    content_data: str = "Python is a programming language."
    ai_enhanced: bool = False
    ai_metadata: Dict = None


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AIVerification")


def test_all_features():
    logger.info("Starting AI Feature Verification with LM Studio")

    # 1. Configuration
    config = RuntimeAIConfig(
        provider="lm_studio",
        model="gguf-gpt-oss-20b-derestricted",
        api_key="not-needed",
        endpoint="http://localhost:1234/v1",
        enable_preprocessing=False,
    )

    service = AIService(config, logger)
    logger.info(
        f"Initialized AIService with Provider: {config.provider}, Model: {config.model}"
    )

    # Mock Data
    mock_user = MockUser()
    mock_content = MockContent()

    results = {}

    try:
        # --- Feature A: Study Plan Generation ---
        logger.info("\n--- [A] Testing Study Plan Generation ---")
        try:
            plan = service.generate_study_plan(
                user=mock_user,
                subject="Python Basics",
                grade_level="Beginner",
                learning_objectives=["Learn variables", "Understand loops"],
                duration_weeks=2,
            )
            logger.info("✅ Study Plan generated successfully")
            if isinstance(plan, dict):
                logger.info(f"   Phases: {len(plan.get('phases', []))}")
            results["StudyPlan"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Study Plan failed: {e}")
            results["StudyPlan"] = f"FAIL: {e}"

        # --- Feature B: Content Enhancement ---
        logger.info("\n--- [B] Testing Content Enhancement ---")
        try:
            enhanced_content = service.enhance_content(
                content=mock_content, enhancement_type="explanation"
            )
            logger.info("✅ Content Enhancement successful")
            logger.info(
                f"   Original length: {len('Python is a programming language.')}"
            )
            logger.info(f"   Enhanced length: {len(enhanced_content.content_data)}")
            results["ContentEnhancement"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Content Enhancement failed: {e}")
            results["ContentEnhancement"] = f"FAIL: {e}"

        # --- Feature C: Exercise Generation ---
        logger.info("\n--- [C] Testing Exercise Generation ---")
        try:
            exercise = service.generate_exercise(
                topic="Python Lists", difficulty="Easy", exercise_type="multiple_choice"
            )
            logger.info("✅ Exercise Generation successful")
            if isinstance(exercise, dict):
                logger.info(f"   Question: {exercise.get('question', '')[:100]}...")
            results["ExerciseGen"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Exercise Generation failed: {e}")
            results["ExerciseGen"] = f"FAIL: {e}"

        # --- Feature D: Lesson Generation ---
        logger.info("\n--- [D] Testing Lesson Generation ---")
        try:
            lesson = service.generate_lesson(
                topic="Variable Types",
                grade_level="Beginner",
                learning_objectives=["Understand integers", "Understand strings"],
                duration_minutes=15,
            )
            logger.info("✅ Lesson Generation successful")
            if isinstance(lesson, dict):
                logger.info(f"   Title: {lesson.get('title')}")
                logger.info(f"   Sections: {len(lesson.get('sections', []))}")
            results["LessonGen"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Lesson Generation failed: {e}")
            results["LessonGen"] = f"FAIL: {e}"

        # --- Feature E: Topic Content Generation ---
        logger.info("\n--- [E] Testing Topic Content Generation ---")
        try:
            topic_content = service.generate_topic_content(
                subject="Computer Science",
                topic_name="For Loops",
                grade_level="Intermediate",
                learning_objectives=["Master for loops", "Iterate lists"],
            )
            logger.info("✅ Topic Content Generation successful")
            if isinstance(topic_content, dict):
                logger.info(f"   Topic: {topic_content.get('topic')}")
            results["TopicContent"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Topic Content Generation failed: {e}")
            results["TopicContent"] = f"FAIL: {e}"

        # --- Feature F: Assessment Question Generation ---
        logger.info("\n--- [F] Testing Assessment Question Generation ---")
        try:
            questions = service.generate_assessment_questions(
                topic="Python Syntax",
                learning_objectives=["Identify syntax errors"],
                difficulty="Beginner",
                num_questions=2,
            )
            logger.info("✅ Assessment Question Generation successful")
            logger.info(f"   Count: {len(questions)}")
            results["AssessmentQ_Gen"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Assessment Question Generation failed: {e}")
            results["AssessmentQ_Gen"] = f"FAIL: {e}"

        # --- Feature G: Course Outline Generation ---
        logger.info("\n--- [G] Testing Course Outline Generation ---")
        try:
            outline = service.generate_course_outline(
                subject="Data Science 101", grade_level="Beginner", duration_weeks=4
            )
            logger.info("✅ Course Outline Generation successful")
            if isinstance(outline, dict):
                logger.info(f"   Units: {len(outline.get('units', []))}")
            results["CourseOutline"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Course Outline Generation failed: {e}")
            results["CourseOutline"] = f"FAIL: {e}"

        # --- Feature H: AI Tutor (Chat) ---
        logger.info("\n--- [H] Testing AI Tutor (Chat) ---")
        try:
            response = service.provide_tutoring(
                user=mock_user,
                question="Explain what a boolean is.",
            )
            logger.info("✅ AI Tutor Chat successful")
            if isinstance(response, dict):
                logger.info(f"   Response: {response.get('answer', '')[:100]}...")
            results["AITutor"] = "PASS"
        except Exception as e:
            logger.error(f"❌ AI Tutor Chat failed: {e}")
            results["AITutor"] = f"FAIL: {e}"

        # --- Feature I: Grading/Feedback ---
        logger.info("\n--- [I] Testing Grading/Feedback ---")
        try:
            grade_result = service.grade_answer(
                question="What is the keyword to define a function in Python?",
                correct_answer="def",
                answer="function",  # Student answer
                question_type="short_answer",
            )
            logger.info("✅ Grading successful")
            if isinstance(grade_result, dict):
                logger.info(f"   Score: {grade_result.get('score', 0)}")
                logger.info(f"   Feedback: {grade_result.get('feedback', '')}")
            results["Grading"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Grading failed: {e}")
            results["Grading"] = f"FAIL: {e}"

        # --- Feature J: Full Assessment Generation ---
        logger.info("\n--- [J] Testing Full Assessment Generation ---")
        try:
            assessment = service.generate_assessment(
                topic="Functions",
                difficulty="Beginner",
                question_types=["multiple_choice"],
                num_questions=3,
            )
            logger.info("✅ Full Assessment Generation successful")
            if isinstance(assessment, dict):
                logger.info(f"   Questions: {len(assessment.get('questions', []))}")
            results["FullAssessment"] = "PASS"
        except Exception as e:
            logger.error(f"❌ Full Assessment Generation failed: {e}")
            results["FullAssessment"] = f"FAIL: {e}"

    except Exception as e:
        logger.critical(f"Critical script failure: {e}")

    # Summary
    print("\n" + "=" * 40)
    print("VERIFICATION RESULTS")
    print("=" * 40)
    passed = 0
    for feature, status in results.items():
        print(f"{feature:<20} : {status}")
        if status == "PASS":
            passed += 1

    print("-" * 40)
    print(f"Total Passed: {passed}/{len(results)}")
    print("=" * 40)


if __name__ == "__main__":
    test_all_features()
