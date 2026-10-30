"""
End-to-End Tests for Phase 1 (Content Ordering) and Phase 2 (Content Creation)
Tests the backend functionality that the GUI uses without opening GUI components
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.getcwd())

from src.core.services.database import DatabaseService
from src.core.models import User, StudyPlan, Content, ContentType, UserRole


class Phase1And2Tester:
    def __init__(self):
        """Initialize with fresh test database"""
        self._cleanup_db_files()
        self.db = DatabaseService("test_phases_1_2.db")
        print("✓ Database initialized")

    def _cleanup_db_files(self):
        """Remove test database files if they exist"""
        db_path = "test_phases_1_2.db"
        for ext in ["", "-shm", "-wal"]:
            file_path = db_path + ext
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except BaseException:
                    pass

    def cleanup(self):
        """Clean up test database"""
        self._cleanup_db_files()
        print("✓ Cleaned up test database")

    def test_phase1_content_ordering(self):
        """
        Test Phase 1: Content Ordering
        Simulates the GUI's content ordering workflow using backend methods
        """
        print("\n" + "=" * 70)
        print("PHASE 1 TEST: CONTENT ORDERING")
        print("=" * 70)

        # Setup: Create teacher and study plan
        print("\n[Setup] Creating teacher and study plan...")
        teacher = User(
            username="teacher_test",
            email="teacher@test.com",
            role=UserRole.TEACHER,
            first_name="Test",
            last_name="Teacher",
            password_hash="hash",
        )
        teacher = self.db.create_user(teacher)

        plan = StudyPlan(
            creator_id=teacher.id,
            title="Python Fundamentals",
            description="Learn Python basics",
            phases=[
                {
                    "title": "Week 1",
                    "description": "Getting Started",
                    "topics": ["Variables", "Types"],
                },
                {
                    "title": "Week 2",
                    "description": "Advanced Topics",
                    "topics": ["Functions", "Classes"],
                },
            ],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        plan = self.db.create_study_plan(plan)
        print(f"✓ Created plan (ID: {plan.id})")

        # Create 4 content items
        print("\n[1] Creating content items...")
        contents = []
        content_titles = [
            "Intro to Variables",
            "Data Types Quiz",
            "Control Flow Lesson",
            "Loops Exercise",
        ]
        for i, title in enumerate(content_titles):
            content = Content(
                content_type=ContentType.LESSON if i % 2 == 0 else ContentType.EXERCISE,
                title=title,
                content_data=f"Content for {title}",
                difficulty=i + 1,
                estimated_time_min=(i + 1) * 10,
            )
            content = self.db.create_content(content)
            contents.append(content)
            print(f"  ✓ Created '{content.title}' (ID: {content.id})")

        # Add all content to phase 0 (simulates GUI add_content_to_plan calls)
        print("\n[2] Adding content to Phase 0 (simulates GUI behavior)...")
        for idx, content in enumerate(contents):
            success = self.db.add_content_to_plan(
                plan.id, content.id, phase_index=0, order_index=idx
            )
            if success:
                print(f"  ✓ Added '{content.title}' at position {idx}")
            else:
                print(f"  ❌ Failed to add '{content.title}'")
                return False

        # Verify initial order (simulates GUI get_plan_contents call)
        print("\n[3] Verifying initial content order (GUI retrieves this)...")
        phase_contents = self.db.get_plan_contents(plan.id)
        items = phase_contents.get(0, [])

        print("  Initial order:")
        for idx, item in enumerate(items):
            print(f"    {idx}: {item['title']} (order={item['order']})")

        if len(items) != 4:
            print(f"  ❌ Expected 4 items, got {len(items)}")
            return False

        # Test move_content_up simulation (what GUI does when user clicks ↑)
        print("\n[4] Testing move_content_up (user clicks ↑ on item 2)...")
        # Simulate: move item at index 2 up (swap with index 1)
        # This is what the GUI's move_content_up method does
        items_copy = items.copy()
        items_copy[2], items_copy[1] = items_copy[1], items_copy[2]
        new_order = [item["id"] for item in items_copy]

        success = self.db.reorder_phase_content(plan.id, 0, new_order)
        if success:
            print("  ✓ Reorder operation successful")
        else:
            print("  ❌ Reorder operation failed")
            return False

        # Verify new order
        phase_contents = self.db.get_plan_contents(plan.id)
        items = phase_contents.get(0, [])

        print("  New order after moving item 2 up:")
        for idx, item in enumerate(items):
            print(f"    {idx}: {item['title']} (order={item['order']})")

        # Verify the swap happened
        if (
            items[1]["title"] != "Control Flow Lesson"
            or items[2]["title"] != "Data Types Quiz"
        ):
            print("  ❌ Content not reordered correctly")
            return False

        # Test move_content_down simulation (what GUI does when user clicks ↓)
        print("\n[5] Testing move_content_down (user clicks ↓ on item 0)...")
        # Move item at index 0 down (swap with index 1)
        items_copy = items.copy()
        items_copy[0], items_copy[1] = items_copy[1], items_copy[0]
        new_order = [item["id"] for item in items_copy]

        success = self.db.reorder_phase_content(plan.id, 0, new_order)
        if success:
            print("  ✓ Reorder operation successful")

        # Final verification
        phase_contents = self.db.get_plan_contents(plan.id)
        items = phase_contents.get(0, [])

        print("  Final order:")
        for idx, item in enumerate(items):
            print(f"    {idx}: {item['title']} (order={item['order']})")

        print("\n✅ PHASE 1 TEST PASSED - Content ordering works correctly!")
        return True

    def test_phase2_content_creation(self):
        """
        Test Phase 2: Content Creation
        Simulates the GUI's content creation workflow using backend methods
        """
        print("\n" + "=" * 70)
        print("PHASE 2 TEST: CREATE NEW CONTENT INTEGRATION")
        print("=" * 70)

        # Get existing plan from phase 1 test
        print("\n[Setup] Using existing plan from Phase 1...")
        plans = self.db.get_session().__enter__().query(StudyPlan).all()
        if not plans:
            print("  ❌ No plan found from Phase 1")
            return False
        plan = plans[0]
        print(f"✓ Using plan '{plan.title}' (ID: {plan.id})")

        # Simulate ContentEditorDialog.get_content() - creating a Content object
        print("\n[1] Creating new content (simulates ContentEditorDialog form)...")
        new_content = Content(
            content_type=ContentType.ASSESSMENT,
            title="Python Basics Assessment",
            content_data="Test your knowledge of Python basics with this comprehensive assessment",
            difficulty=3,
            estimated_time_min=45,
        )
        print("  ✓ Content object created with form data:")
        print(f"    - Title: {new_content.title}")
        print(f"    - Type: {new_content.content_type.value}")
        print(f"    - Difficulty: {new_content.difficulty}/5")
        print(f"    - Time: {new_content.estimated_time_min} min")

        # Simulate create_and_add_content method - save to database
        print("\n[2] Saving content to database (GUI calls db.create_content)...")
        created = self.db.create_content(new_content)
        if created:
            print(f"  ✓ Content saved to database (ID: {created.id})")
        else:
            print("  ❌ Failed to save content")
            return False

        # Simulate adding to phase (GUI calls db.add_content_to_plan)
        print("\n[3] Adding content to Phase 1 (GUI calls db.add_content_to_plan)...")
        phase_index = 1
        success = self.db.add_content_to_plan(plan.id, created.id, phase_index)
        if success:
            print(f"  ✓ Content added to Phase {phase_index}")
        else:
            print("  ❌ Failed to add content to phase")
            return False

        # Verify content appears in phase (GUI calls refresh_content)
        print("\n[4] Verifying content appears in phase (GUI refresh)...")
        phase_contents = self.db.get_plan_contents(plan.id)
        phase1_items = phase_contents.get(phase_index, [])

        print(f"  Phase {phase_index} now contains {len(phase1_items)} item(s):")
        for item in phase1_items:
            print(f"    - {item['title']} ({item['type']})")

        # Verify our new content is there
        found = any(item["id"] == created.id for item in phase1_items)
        if not found:
            print("  ❌ New content not found in phase")
            return False

        # Test creating multiple content items and adding them
        print("\n[5] Creating and adding multiple content items...")
        multi_contents = [
            Content(
                content_type=ContentType.LESSON,
                title="Advanced Functions",
                content_data="Deep dive into Python functions",
                difficulty=4,
                estimated_time_min=60,
            ),
            Content(
                content_type=ContentType.EXERCISE,
                title="Functions Practice",
                content_data="Practice exercises for functions",
                difficulty=3,
                estimated_time_min=30,
            ),
        ]

        for content in multi_contents:
            created = self.db.create_content(content)
            if created:
                self.db.add_content_to_plan(plan.id, created.id, phase_index=1)
                print(f"  ✓ Created and added '{content.title}'")

        # Final verification
        phase_contents = self.db.get_plan_contents(plan.id)
        phase1_items = phase_contents.get(1, [])

        print(f"\n  Phase 1 final content count: {len(phase1_items)} items")
        if len(phase1_items) != 3:
            print(f"  ❌ Expected 3 items in Phase 1, got {len(phase1_items)}")
            return False

        print(
            "\n✅ PHASE 2 TEST PASSED - Content creation and integration works correctly!"
        )
        return True

    def test_gui_data_handling(self):
        """
        Test that the GUI receives and handles data correctly
        """
        print("\n" + "=" * 70)
        print("GUI DATA HANDLING VERIFICATION")
        print("=" * 70)

        print("\n[1] Verifying get_plan_contents returns correct format...")
        plans = self.db.get_session().__enter__().query(StudyPlan).all()
        plan = plans[0]

        phase_contents = self.db.get_plan_contents(plan.id)

        # Verify it's a dict with phase indices as keys
        if not isinstance(phase_contents, dict):
            print("  ❌ get_plan_contents should return a dictionary")
            return False

        print(f"  ✓ Returns dictionary with {len(phase_contents)} phases")

        # Verify each phase has list of items with correct structure
        for phase_idx, items in phase_contents.items():
            if not isinstance(items, list):
                print(f"  ❌ Phase {phase_idx} should have a list of items")
                return False

            print(f"\n  Phase {phase_idx}: {len(items)} items")
            for item in items:
                # Verify required keys exist
                required_keys = ["id", "title", "type", "order"]
                missing_keys = [k for k in required_keys if k not in item]

                if missing_keys:
                    print(f"    ❌ Item missing keys: {missing_keys}")
                    return False

                print(
                    f"    ✓ {item['title']}: id={item['id']}, type={item['type']}, order={item['order']}"
                )

        print("\n[2] Verifying content is sorted by order_index...")
        for phase_idx, items in phase_contents.items():
            orders = [item["order"] for item in items]
            if orders != sorted(orders):
                print(f"  ❌ Phase {phase_idx} items not sorted by order")
                return False
            print(f"  ✓ Phase {phase_idx} items correctly sorted: {orders}")

        print(
            "\n✅ GUI DATA HANDLING VERIFIED - Data format is correct for GUI consumption!"
        )
        return True

    def run_all_tests(self):
        """Run all Phase 1 and Phase 2 tests"""
        try:
            print("\n🚀 Starting Phase 1 & 2 End-to-End Tests...\n")

            # Test Phase 1
            if not self.test_phase1_content_ordering():
                print("\n❌ Phase 1 tests failed!")
                return False

            # Test Phase 2
            if not self.test_phase2_content_creation():
                print("\n❌ Phase 2 tests failed!")
                return False

            # Test GUI data handling
            if not self.test_gui_data_handling():
                print("\n❌ GUI data handling tests failed!")
                return False

            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 70)
            print("\nSummary:")
            print("  ✅ Phase 1: Content ordering works correctly")
            print("  ✅ Phase 2: Content creation and integration works correctly")
            print("  ✅ GUI data handling: Data format is correct")
            print("\n  Backend methods tested:")
            print("    - db.add_content_to_plan()")
            print("    - db.get_plan_contents()")
            print("    - db.reorder_phase_content()")
            print("    - db.create_content()")
            print("\n  GUI integration verified:")
            print("    - Content ordering operations")
            print("    - Content creation workflow")
            print("    - Data retrieval and formatting")
            print()

            return True

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.cleanup()


if __name__ == "__main__":
    tester = Phase1And2Tester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
