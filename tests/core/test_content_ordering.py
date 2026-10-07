"""
Test content ordering functionality
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.fixtures.synthetic_database import new_synthetic_database
from src.core.models import User, StudyPlan, Content, ContentType, UserRole


def test_content_ordering(tmp_path):
    """Test the content ordering feature on a new disposable database."""
    db = new_synthetic_database(tmp_path / "ordering.sqlite3")

    try:
        print("\n🧪 Testing Content Ordering Feature...")
        print("=" * 60)

        # Create teacher
        teacher = User(
            username="teacher",
            email="teacher@test.com",
            role=UserRole.TEACHER,
            first_name="Test",
            last_name="Teacher",
            password_hash="test",
        )
        teacher = db.create_user(teacher)
        print(f"✓ Created teacher (ID: {teacher.id})")

        # Create study plan
        plan = StudyPlan(
            creator_id=teacher.id,
            title="Test Plan",
            description="Testing ordering",
            phases=[
                {
                    "title": "Phase 1",
                    "description": "First phase",
                    "topics": ["Topic 1"],
                }
            ],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        plan = db.create_study_plan(plan)
        print(f"✓ Created plan (ID: {plan.id})")

        # Create 4 content items
        contents = []
        for i in range(1, 5):
            content = Content(
                content_type=ContentType.LESSON,
                title=f"Content {i}",
                content_data=f"Content {i} data",
                difficulty=i,
                estimated_time_min=10 * i,
            )
            content = db.create_content(content)
            contents.append(content)
            print(f"✓ Created content '{content.title}' (ID: {content.id})")

        # Add all content to phase 0
        print("\nAdding content to Phase 0...")
        for idx, content in enumerate(contents):
            db.add_content_to_plan(plan.id, content.id, phase_index=0, order_index=idx)
            print(f"  Added '{content.title}' at position {idx}")

        # Verify initial order
        print("\nInitial order:")
        phase_contents = db.get_plan_contents(plan.id)
        items = phase_contents.get(0, [])
        for idx, item in enumerate(items):
            print(f"  {idx}: {item['title']} (order={item['order']})")

        # Test reordering - move items around
        print(
            "\nReordering: [Content 1, Content 2, Content 3, Content 4] -> [Content 2, Content 4, Content 1, Content 3]"
        )
        new_order = [contents[1].id, contents[3].id, contents[0].id, contents[2].id]
        success = db.reorder_phase_content(plan.id, 0, new_order)

        assert success, "Reorder operation failed"
        print("✓ Reorder operation successful")

        # Verify new order
        print("\nNew order after reordering:")
        phase_contents = db.get_plan_contents(plan.id)
        items = phase_contents.get(0, [])
        expected_titles = ["Content 2", "Content 4", "Content 1", "Content 3"]

        for idx, item in enumerate(items):
            print(f"  {idx}: {item['title']} (order={item['order']})")
            assert (
                item["title"] == expected_titles[idx]
            ), f"Expected '{expected_titles[idx]}' but got '{item['title']}'"

        print("\n" + "=" * 60)
        print("✅ CONTENT ORDERING TEST PASSED!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    with TemporaryDirectory(prefix="slm-ordering-") as directory:
        test_content_ordering(Path(directory))
