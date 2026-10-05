"""Canonical, bounded source sections shared by learner render and tutor inputs."""

from hashlib import sha256
import json
import re
from pydantic import BaseModel, Field

from .content_schema import normalize_content, learner_content

CONTEXT_CHAR_LIMIT = 6000
PROMPT_VERSION = "teacher-reviewed-v3-bounded-generation"
SECTION_CHAR_LIMIT = 1800


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
    fragment_hash: str = ""
    available_sections: list[dict] = Field(default_factory=list)
    selection: str = "bounded_default"


def canonical_visible(content) -> dict:
    """Return exactly the instructional representation used by learner reads."""
    data = content.decrypted_content_data
    if data is None and content.content_data:
        raise ValueError("Source is unavailable; its encryption key may not match")
    try:
        return learner_content(
            content.content_type.value,
            normalize_content(content.content_type.value, data or {}),
        )
    except ValueError as error:
        raise ValueError(
            f"This source has no readable canonical content: {error}"
        ) from error


def content_revision(content) -> str:
    """Instructional-text identity excludes hidden keys; exam pointers retain local linkage."""
    return sha256(
        json.dumps(
            canonical_visible(content), sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


def _sections(content) -> list[tuple[str, str, str]]:
    data = canonical_visible(content)
    sections = []
    if content.content_type.value == "lesson":
        for index, section in enumerate(data.get("sections", [])):
            sections.append(
                (
                    f"section-{index + 1}",
                    section.get("title", ""),
                    section.get("content", ""),
                )
            )
    else:
        for key in ("question", "question_text", "instructions", "content", "hint"):
            if isinstance(data.get(key), str):
                sections.append((key, key, data[key]))
    for key in ("summary", "objectives", "key_concepts", "vocabulary"):
        value = data.get(key)
        if value:
            sections.append(
                (
                    key,
                    key,
                    (
                        value
                        if isinstance(value, str)
                        else json.dumps(value, ensure_ascii=False)
                    ),
                )
            )
    parts = []
    for reference, title, text in sections:
        if not text.strip():
            continue
        for offset in range(0, len(text), SECTION_CHAR_LIMIT):
            suffix = (
                f"-part-{offset // SECTION_CHAR_LIMIT + 1}"
                if len(text) > SECTION_CHAR_LIMIT
                else ""
            )
            parts.append(
                (
                    f"content:{content.id}/{reference}{suffix}",
                    title,
                    text[offset : offset + SECTION_CHAR_LIMIT],
                )
            )
    return parts


def source_context(
    content, *, section_ids: list[str] | None = None, query: str | None = None
) -> SourceContext:
    """Select actual authorized sections, including late sections, within one budget."""
    return combined_source_context(
        [content],
        content.id,
        content.title,
        content.content_type.value,
        section_ids=section_ids,
        query=query,
    )


def combined_source_context(
    contents,
    source_id: int,
    title: str,
    source_type: str = "course",
    *,
    section_ids: list[str] | None = None,
    query: str | None = None,
) -> SourceContext:
    """Build a bounded view over the canonical course graph without hidden keys."""
    sections = [part for content in contents for part in _sections(content)]
    if not sections:
        raise ValueError(
            "This source has no readable lesson or practice text. Choose a lesson or ask without source context."
        )
    available = [
        {"id": ref, "title": label, "characters": len(text)}
        for ref, label, text in sections
    ]
    known = {ref for ref, _, _ in sections}
    if section_ids and (
        len(set(section_ids)) != len(section_ids)
        or not set(section_ids).issubset(known)
    ):
        raise ValueError("Selected sections do not belong to this source revision")
    selected = [item for item in sections if not section_ids or item[0] in section_ids]
    terms = set(re.findall(r"\w{3,}", (query or "").lower()))
    if terms and not section_ids:
        selected = sorted(
            selected,
            key=lambda item: -len(
                terms & set(re.findall(r"\w{3,}", (item[1] + " " + item[2]).lower()))
            ),
        )
    blocks: list[str] = []
    refs: list[str] = []
    used = 0
    for ref, label, text in selected:
        prefix = f"[{ref}] {label}\n"
        remaining = CONTEXT_CHAR_LIMIT - used - (2 if blocks else 0)
        if remaining <= len(prefix):
            break
        block = (prefix + text)[:remaining]
        blocks.append(block)
        refs.append(ref)
        used += len(block) + (2 if len(blocks) > 1 else 0)
    included = "\n\n".join(blocks)
    complete = "\n\n".join(f"[{ref}] {label}\n{text}" for ref, label, text in sections)
    version = sha256(
        json.dumps(
            [
                {"title": content.title, "revision": content_revision(content)}
                for content in contents
            ],
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return SourceContext(
        id=source_id,
        title=title,
        type=source_type,
        content_data=included,
        source_version=version,
        references=refs,
        truncated=len(included) < len(complete),
        included_characters=len(included),
        total_characters=len(complete),
        fragment_hash=sha256(included.encode()).hexdigest(),
        available_sections=available,
        selection=(
            "explicit_sections"
            if section_ids
            else "query_sections" if terms else "bounded_default"
        ),
    )
