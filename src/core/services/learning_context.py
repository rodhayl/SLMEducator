"""A bounded, source-labelled contract shared by tutor routes and prompts."""

from hashlib import sha256
from typing import Any
from pydantic import BaseModel

CONTEXT_CHAR_LIMIT = 6000
PROMPT_VERSION = "teacher-reviewed-v1"


class SourceContext(BaseModel):
    id: int
    title: str
    type: str
    content_data: str
    source_version: str
    references: list[str]
    truncated: bool
    included_characters: int
    total_characters: int


def source_context(content) -> SourceContext:
    """Extract authorized learner-visible text; never add answer keys or rubrics."""
    data = content.decrypted_content_data
    if data is None and content.content_data:
        raise ValueError("Source is unavailable; its encryption key may not match")
    data = data or {}
    sections: list[tuple[str, str]] = []
    for key in ("content", "text", "body", "summary"):
        if (
            isinstance(data.get(key), str)
            and data[key].strip()
            and (not data.get("sections") or key == "summary")
        ):
            sections.append((key, data[key]))
    for index, section in enumerate(data.get("sections", []) or []):
        if isinstance(section, dict):
            text = str(section.get("content") or section.get("text") or "")
            sections.append((f"section-{index + 1}: {section.get('title', '')}", text))
    for key in ("question", "question_text", "instructions", "hint"):
        if isinstance(data.get(key), str):
            sections.append((key, data[key]))
    texts = [f"[content:{content.id}/{ref}]\n{text}" for ref, text in sections]
    complete = "\n\n".join(texts)
    if not any(text.strip() for _, text in sections):
        raise ValueError(
            "This source has no readable lesson or practice text. Choose a lesson or ask without source context."
        )
    included = complete[:CONTEXT_CHAR_LIMIT]
    return SourceContext(
        id=content.id,
        title=content.title,
        type=content.content_type.value,
        content_data=included,
        source_version=sha256(complete.encode()).hexdigest(),
        references=[
            f"content:{content.id}/{ref}"
            for ref, _ in sections
            if f"[content:{content.id}/{ref}]" in included
        ],
        truncated=len(complete) > CONTEXT_CHAR_LIMIT,
        included_characters=len(included),
        total_characters=len(complete),
    )
