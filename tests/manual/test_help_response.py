import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.database import DatabaseService
from src.core.models import User, HelpRequest
from datetime import datetime


def test_help_response():
    db_service = DatabaseService()
    db = db_service.get_session()
    try:
        # Get the request we created (assuming ID=4 based on previous output, or find by text)
        req = (
            db.query(HelpRequest)
            .filter(
                HelpRequest.request_text
                == "Stuck on math: Phase 1 test request manual insertion"
            )
            .first()
        )
        if not req:
            print("❌ Help request not found.")
            return

        print(f"Found request ID: {req.id}, Status: {req.status}")

        # Simulate Teacher Response (Backend Logic)
        teacher = db.query(User).filter(User.username == "tester_unique_123").first()

        # In actual app, response is sent via message or internal note.
        # The 'Resolve' action updates status.

        # 1. Update Resolution Notes
        req.resolution_notes = "AI Draft used. Manual edit: Here is some help."

        # 2. Mark as Resolved
        req.status = "resolved"
        req.resolved_by_id = teacher.id
        req.resolved_at = datetime.now()

        db.commit()
        db.refresh(req)

        print(f"✅ Request resolved. New Status: {req.status}")
        print(f"✅ Resolution Notes: {req.resolution_notes}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_help_response()
