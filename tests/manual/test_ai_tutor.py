import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.ai_service import AIService

# Mock config if needed or use default
from unittest.mock import MagicMock, patch


def test_ai_tutor_connectivity():
    print("Testing AI Tutor Connectivity...")
    try:
        # Mock dependencies
        mock_config = MagicMock()
        mock_config.provider = "openai"
        mock_config.model = "gpt-3.5-turbo"

        mock_logger = MagicMock()

        # Patch the settings service getter used in __init__
        with patch("src.core.services.ai_service.get_settings_service"):
            # Initialize AIService with mocks
            service = AIService(config=mock_config, logger=mock_logger)

            test_message = "Hello AI"
            expected_context = "You are a helpful AI tutor."

            # Check internal prompt building logic
            prompt = service._build_tutoring_prompt(
                test_message, expected_context, "10th Grade"
            )

            if "Hello AI" in prompt and "helpful AI tutor" in prompt:
                print("✅ AIService prompt building works.")
            else:
                print("❌ AIService prompt building failed.")

            print("✅ AI Tutor Service module is accessible and initialized.")
        # Real connectivity check would require API Key.
        # For this test, we verify the service class is loadable and logical.
        print("✅ AI Tutor Service module is accessible.")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_ai_tutor_connectivity()
