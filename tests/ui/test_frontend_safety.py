"""Source/asset contracts; functional DOM cases run separately with npm test."""
import hashlib
import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "src" / "web"


def test_pinned_local_assets_match_reviewed_manifest():
    """All vendored distributions retain their recorded hashes and licenses."""
    vendor = WEB / "static" / "vendor"
    manifest = json.loads((vendor / "manifest.json").read_text())
    assert "dompurify" in manifest["sources"]
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((vendor / name).read_bytes()).hexdigest() == expected
    assert "DOMPurify" in (vendor / "dompurify@3.4.16/purify.min.js").read_text()


def test_pages_load_safe_helpers_before_application_scripts_without_cdn():
    """Offline pages load the same renderer and no unpinned remote JS/CSS."""
    for page in WEB.glob("*.html"):
        source = page.read_text()
        assert "https://cdn" not in source
        assert source.index("purify.min.js") < source.index("safe-render.js")
        assert source.index("safe-render.js") < source.index("</head>")
        assert source.index("learning-client.js") < source.index("time-display.js") < source.index("</head>")
        for url in re.findall(r'(?:src|href)="(/static/[^"?#]+)', source):
            assert (WEB / url.lstrip("/")).is_file(), (page.name, url)


def test_markdown_and_session_rewards_have_one_boundary():
    """Only the shared maintained sanitizer parses Markdown; UI never awards XP."""
    for script in (WEB / "static/js").rglob("*.js"):
        source = script.read_text()
        if script.name != "safe-render.js":
            assert "marked.parse(" not in source, script.name
        assert "/api/gamification/award-xp" not in source, script.name
    source = (WEB / "static/js/session.js").read_text()
    assert "/api/mastery/review" not in source
    assert "session_notes_" not in source


def test_recovery_translations_have_parity_and_required_keys():
    """All new shared recovery/UI strings exist in English and Spanish."""
    translations = WEB.parents[1] / "translations"
    en = json.loads((translations / "en.json").read_text())["recovery"]
    es = json.loads((translations / "es.json").read_text())["recovery"]
    assert en.keys() == es.keys()
    for key in ["reauth", "pending_review", "move_up", "retry_failed", "review_publish", "restore", "discard", "policy_hints_only", "policy_disabled_reason", "timezone_unknown", "timezone_save_failed"]:
        assert en[key] and es[key]


def test_critical_form_labels_and_live_regions():
    """Targeted semantic checks supplement, not replace, real keyboard/screen-reader QA."""
    required = {
        "study_plan_builder.html": ["plan-title", "plan-description", "plan-public"],
        "assessment_builder.html": ["quiz-title", "quiz-desc", "quiz-pass", "grading-mode", "quiz-time", "quiz-attempts", "assessment-assistance"],
        "dashboard.html": ["tutor-assistance", "settings-timezone"],
        "session_player.html": ["difficulty-rating"],
    }
    for page, ids in required.items():
        source = (WEB / page).read_text()
        for identifier in ids:
            assert f'for="{identifier}"' in source
    assert 'role="status"' in (WEB / "assessment_taker.html").read_text()
    assert 'aria-describedby="notes-save-status"' in (WEB / "session_player.html").read_text()
    assert ':focus-visible' in (WEB / "static/css/main.css").read_text()


def test_existing_endpoint_and_publication_contracts():
    """Published assessment/course workflows are explicit, with supported password route."""
    dashboard = (WEB / "static/js/dashboard.js").read_text()
    assert "/api/auth/change-password" in dashboard
    assert "/api/users/change-password" not in dashboard
    builder = (WEB / "static/js/assessment_builder.js").read_text()
    assert "/publish" in builder and "saveAssessmentDraft" in builder
    course = (WEB / "static/js/course_designer.js").read_text()
    assert "/api/generate/full-topic-package" in course
    assert "if (!data?.success || !data.saved_content_ids?.length)" in course


def test_server_timestamps_use_shared_explicit_provenance_boundary():
    """Server instants cannot silently acquire the browser's local timezone."""
    for file in ["dashboard.js", "session.js", "grading.js", "modules/inbox.js"]:
        source = (WEB / "static/js" / file).read_text()
        assert "SLMTime.format(" in source
        assert not re.search(r"new Date\([^)]*(?:created_at|start_time|submitted_at|sent_at|last_login|earned_at|timestamp)", source)
    taker = (WEB / "static/js/assessment_taker.js").read_text()
    assert "SLMTime.epoch(rawDeadline, currentAttempt.timing_provenance)" in taker
    assert "rawDeadline + 'Z'" not in taker


def test_muted_text_tokens_meet_aa_normal_text_contrast():
    """Check two explicit text/background pairs; this is not a complete WCAG audit."""
    def luminance(color):
        values = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    css = (WEB / "static/css/main.css").read_text()
    root_token = re.search(r"--text-muted:\s*(#[0-9a-f]+)", css).group(1)
    dark_section = css.split("body.theme-dark {", 1)[1].split("}", 1)[0]
    dark_token = re.search(r"--text-muted:\s*(#[0-9a-f]+)", dark_section).group(1)
    for foreground, background in [(root_token, "#ffffff"), (dark_token, "#1f2937")]:
        light, dark = sorted([luminance(foreground), luminance(background)], reverse=True)
        assert (light + 0.05) / (dark + 0.05) >= 4.5
