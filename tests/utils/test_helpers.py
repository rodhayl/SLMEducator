"""Helper methods for assess_progress"""


def _build_progress_assessment_prompt(user, learning_session):
    """Build prompt for progress assessment."""
    user_id = user.get("id") if isinstance(user, dict) else user.id
    user_name = user.get("full_name") if isinstance(user, dict) else user.full_name
    grade_level = (
        user.get("grade_level") if isinstance(user, dict) else user.grade_level
    )

    prompt = f"""
    Analyze this student's learning session and provide progress assessment:

    Student: {user_name} (ID: {user_id}, Grade {grade_level})
    Session Duration: {learning_session.duration_minutes} minutes
    Completion Status: {learning_session.completion_status}
    Score: {learning_session.score or 'N/A'}

    Provide assessment in this JSON format:
    {{
        "progress_summary": "Brief summary of progress",
        "strengths": ["strength1", "strength2"],
        "areas_for_improvement": ["area1", "area2"],
        "recommendations": ["recommendation1", "recommendation2"],
        "next_steps": "Suggested next learning activities"
    }}
    """
    return prompt


def _parse_progress_assessment_response(response_content):
    """Parse AI progress assessment response."""
    import json

    try:
        # Find JSON content
        start = response_content.find("{")
        end = response_content.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response_content[start:end]
            return json.loads(json_str)
        else:
            return {
                "progress_summary": "Good progress made",
                "strengths": ["Consistent effort"],
                "areas_for_improvement": ["Continue practicing"],
                "recommendations": ["Keep studying regularly"],
                "next_steps": "Continue with current learning path",
            }
    except Exception:
        return {
            "progress_summary": "Good progress made",
            "strengths": ["Consistent effort"],
            "areas_for_improvement": ["Continue practicing"],
            "recommendations": ["Keep studying regularly"],
            "next_steps": "Continue with current learning path",
        }


# Test
from dataclasses import dataclass


@dataclass
class MockUser:
    id: int
    full_name: str
    grade_level: str


@dataclass
class MockSession:
    id: int
    duration_minutes: int
    completion_status: str
    score: float


user = MockUser(1, "Test Student", "10")
session = MockSession(1, 45, "completed", 85.0)

prompt = _build_progress_assessment_prompt(user, session)
print("Prompt generated successfully")
print(prompt[:200])

response = '{"progress_summary": "test", "strengths": ["a"], "areas_for_improvement": ["b"], "recommendations": ["c"], "next_steps": "d"}'
result = _parse_progress_assessment_response(response)
print("\nParsing test:", result)
