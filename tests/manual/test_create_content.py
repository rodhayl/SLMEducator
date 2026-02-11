import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.database import DatabaseService
from src.core.models import User, Content, ContentType
from datetime import datetime


def test_create_content():
    db_service = DatabaseService()
    db = db_service.get_session()
    try:
        # Check if teacher exists
        teacher = db.query(User).filter(User.username == "tester_unique_123").first()
        if not teacher:
            print("❌ Teacher user not found.")
            return

        print("Simulating Content Creation...")

        # Create Content
        new_content = Content(
            title="Browser Test Lesson 1 (Backend)",
            content_type=ContentType.LESSON,
            content_data='{"text": "This is a test lesson content created via script."}',
            creator_id=teacher.id,
            created_at=datetime.now(),
        )
        db.add(new_content)
        db.commit()
        db.refresh(new_content)

        print(f"✅ Content created successfully. ID: {new_content.id}")
        print(f"Title: {new_content.title}")
        print(f"Type: {new_content.content_type}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_create_content()
