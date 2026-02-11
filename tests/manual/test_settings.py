import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.database import DatabaseService
from src.core.models import User, AIModelConfiguration


def test_settings_db():
    print("Testing AI Model Configuration in DB...")
    db_service = DatabaseService()
    db = db_service.get_session()
    try:
        # 1. Get Teacher User
        teacher = db.query(User).filter(User.username == "tester_unique_123").first()
        if not teacher:
            print("❌ Teacher user not found.")
            return

        # 2. Check for existing config
        config = (
            db.query(AIModelConfiguration)
            .filter(AIModelConfiguration.user_id == teacher.id)
            .first()
        )

        if not config:
            print("Creating new AI Config...")
            config = AIModelConfiguration(
                user_id=teacher.id,
                provider="openai",
                model="gpt-4o",
                temperature=0.7,
                max_tokens=2000,
            )
            db.add(config)
        else:
            print(f"Updating existing AI Config (ID: {config.id})...")
            config.model = "gpt-4o-updated"
            config.temperature = 0.8

        db.commit()
        db.refresh(config)

        print(f"✅ AI Config Saved.")
        print(f"Provider: {config.provider}")
        print(f"Model: {config.model}")
        print(f"Temp: {config.temperature}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_settings_db()
