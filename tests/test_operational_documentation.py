"""Keep maintained recovery and React guides tied to supported entry points."""

import re
import shlex
from pathlib import Path, PureWindowsPath

import pytest

from scripts.recover_database import parser

ROOT = Path(__file__).resolve().parents[1]
CURRENT_GUIDES = (
    "docs/README.md",
    "docs/MIGRATION_GUIDE.md",
    "docs/api/THEME_SYSTEM.md",
    "docs/api/API_THEME_MANAGER.md",
    "docs/i18n/TRANSLATION_GUIDE.md",
    "docs/i18n/TRANSLATION_IMPLEMENTATION_SUMMARY.md",
)


@pytest.mark.parametrize("relative", CURRENT_GUIDES)
def test_current_guides_link_only_to_existing_repository_paths(relative):
    document = ROOT / relative
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
        path = link.split("#", 1)[0]
        assert not re.match(r"[a-z]+://", path), "These are local maintenance guides"
        assert (document.parent / path).exists(), f"{relative}: {link}"


def test_migration_guide_is_copy_first_and_keeps_keys_private():
    guide = (ROOT / "docs/MIGRATION_GUIDE.md").read_text()
    for obsolete in (
        "migrate_encryption_key.py", "old_encryption_key.txt", "rm slm_educator.db",
        "cp slm_educator.db", "echo $SLM_ENCRYPTION_KEY", "Remove-Item",
    ):
        assert obsolete not in guide
    for requirement in (
        "PORTABILITY_RECOVERY.md", "copy-first", "committed WAL", "original encryption key",
        "stop the old application", "SLM_DB_PATH", "Existing output files",
        "does not switch", "never print it",
    ):
        assert requirement in guide


def test_documented_recovery_commands_parse_without_reading_data():
    guide = (ROOT / "docs/MIGRATION_GUIDE.md").read_text()
    commands = [line for line in guide.splitlines() if "scripts\\recover_database.py " in line]
    modes = []
    for command in commands:
        arguments = shlex.split(command, posix=False)[2:]
        parsed = parser().parse_args(arguments)
        modes.append(parsed.command)
        paths = [getattr(parsed, name, None) for name in ("database", "backup", "output")]
        selected = [str(path) for path in paths if path is not None]
        assert all(PureWindowsPath(path).is_absolute() for path in selected)
        assert len(selected) == len(set(selected)), "Source and destination must differ"
    assert modes == ["backup", "restore", "inspect", "upgrade", "inspect"]


def test_active_ui_guides_do_not_prescribe_removed_qt_modules():
    guides = "\n".join((ROOT / path).read_text() for path in CURRENT_GUIDES)
    for obsolete in ("src.ui.i18n", "src/ui/", "ui.styles.theme", "QLabel(", "QPushButton("):
        assert obsolete not in guides
    contributing = (ROOT / "docs/CONTRIBUTING.md").read_text()
    section = contributing.split("### Internationalization (i18n)", 1)[1].split("###", 1)[0]
    assert "data-i18n" not in section
    assert "react-i18next" in section
    assert "locales.ts" in section
    assert "common.ts" in section


def test_react_docs_describe_real_locale_and_appearance_boundaries():
    locale = (ROOT / "docs/i18n/TRANSLATION_GUIDE.md").read_text()
    for term in ("Spanish", "fallback", "slm-language", "{{name}}", "useTranslation", "registerLocales"):
        assert term in locale
    appearance = (ROOT / "docs/api/THEME_SYSTEM.md").read_text()
    for term in ("slm-theme", "slm-reading-size", "16", "18", "20", "24", "prefers-reduced-motion"):
        assert term in appearance
    assert "no separate localStorage entry" in appearance
    summary = (ROOT / "docs/i18n/TRANSLATION_IMPLEMENTATION_SUMMARY.md").read_text()
    assert "/api/settings/translations/{lang}" in summary
    assert "src/starter.py" in summary


def test_attributes_retire_vendor_rules_but_preserve_historical_hash_controls():
    attributes = (ROOT / ".gitattributes").read_text()
    assert "src/web/static/vendor" not in attributes
    for path in (
        "implementation_documents/v10_single_pass_evidence/**",
        "implementation_documents/v11_final_pass_evidence/**",
        "implementation_documents/lesson_claim_consistency_20261006_final_pass_report.md",
        "implementation_documents/v10_*.py",
        "implementation_documents/source_trust_20261006_single_pass_report.md",
    ):
        assert f"{path} -text whitespace=cr-at-eol" in attributes
    assert "harness_guard.diff -text whitespace=-blank-at-eol,-blank-at-eof,cr-at-eol" in attributes
