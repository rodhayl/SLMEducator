"""
Test suite for style standardization across SLM Educator HTML pages.
Verifies Bootstrap version consistency, CSS imports, and navbar patterns.
"""

import re
import pytest
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

WEB_DIR = Path(__file__).parent.parent.parent / "src" / "web"
EXPECTED_BOOTSTRAP_VERSION = "5.3.0"
REQUIRED_MAIN_CSS = "/static/css/main.css"


def get_html_files():
    """Get all HTML files in the web directory."""
    return list(WEB_DIR.glob("*.html"))


# ============================================================================
# Test: Bootstrap Version Consistency
# ============================================================================


class TestBootstrapVersions:
    """Verify all HTML files use consistent Bootstrap versions."""

    @pytest.fixture
    def html_files(self):
        """Get list of all HTML files."""
        files = get_html_files()
        assert len(files) > 0, "No HTML files found in web directory"
        return files

    def test_bootstrap_css_version(self, html_files):
        """All pages should use Bootstrap CSS version 5.3.0."""
        failures = []
        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            matches = re.findall(r"bootstrap@(\d+\.\d+\.\d+)/dist/css", content)
            if not matches:
                failures.append(f"{html_file.name}: No Bootstrap CSS found")
            elif matches[0] != EXPECTED_BOOTSTRAP_VERSION:
                failures.append(
                    f"{html_file.name}: Bootstrap CSS is {matches[0]}, expected {EXPECTED_BOOTSTRAP_VERSION}"
                )

        assert not failures, "Bootstrap CSS version mismatches:\n" + "\n".join(failures)

    def test_bootstrap_js_version_consistency(self, html_files):
        """Pages that include Bootstrap JS should use the same version as CSS."""
        failures = []
        pages_requiring_js = [
            "dashboard.html",
            "course_designer.html",
            "assessment_builder.html",
            "assessment_taker.html",
            "grading.html",
            "session_player.html",
            "study_plan_builder.html",
        ]

        for html_file in html_files:
            if html_file.name not in pages_requiring_js:
                continue  # Skip auth pages that don't need modals/dropdowns

            content = html_file.read_text(encoding="utf-8")
            js_matches = re.findall(r"bootstrap@(\d+\.\d+\.\d+)/dist/js", content)

            if not js_matches:
                failures.append(
                    f"{html_file.name}: Missing Bootstrap JS (required for modals/dropdowns)"
                )
            elif js_matches[0] != EXPECTED_BOOTSTRAP_VERSION:
                failures.append(
                    f"{html_file.name}: Bootstrap JS is {js_matches[0]}, expected {EXPECTED_BOOTSTRAP_VERSION}"
                )

        assert not failures, "Bootstrap JS version issues:\n" + "\n".join(failures)


# ============================================================================
# Test: Main CSS Import
# ============================================================================


class TestMainCSSImport:
    """Verify all HTML files import main.css."""

    @pytest.fixture
    def html_files(self):
        return get_html_files()

    def test_all_pages_import_main_css(self, html_files):
        """All pages must import the main.css stylesheet."""
        failures = []
        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            if REQUIRED_MAIN_CSS not in content and "main.css" not in content:
                failures.append(html_file.name)

        assert not failures, f"Pages missing main.css import: {failures}"


# ============================================================================
# Test: No Inline Style Blocks
# ============================================================================


class TestNoInlineStyleBlocks:
    """Verify no <style> blocks exist in HTML files."""

    @pytest.fixture
    def html_files(self):
        return get_html_files()

    def test_no_style_blocks(self, html_files):
        """No HTML file should contain <style> blocks (all styles should be in main.css)."""
        failures = []
        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            if "<style>" in content.lower():
                failures.append(html_file.name)

        assert not failures, f"Pages with inline <style> blocks: {failures}"


# ============================================================================
# Test: CSS Design System Variables
# ============================================================================


class TestCSSDesignSystem:
    """Verify main.css contains required design system components."""

    @pytest.fixture
    def main_css(self):
        css_path = WEB_DIR / "static" / "css" / "main.css"
        assert css_path.exists(), "main.css not found"
        return css_path.read_text(encoding="utf-8")

    def test_css_variables_defined(self, main_css):
        """main.css should define core CSS variables."""
        required_vars = [
            "--primary-color",
            "--bg-body",
            "--text-primary",
            "--border-color",
            "--spacing-md",
            "--radius-md",
        ]
        missing = [var for var in required_vars if var not in main_css]
        assert not missing, f"Missing CSS variables: {missing}"

    def test_step_indicator_styles(self, main_css):
        """main.css should include step indicator component styles."""
        required_classes = [".step-indicator", ".step-circle", ".step-label"]
        missing = [cls for cls in required_classes if cls not in main_css]
        assert not missing, f"Missing step indicator classes: {missing}"

    def test_outline_tree_styles(self, main_css):
        """main.css should include outline tree component styles."""
        required_classes = [
            ".outline-tree",
            ".unit-item",
            ".unit-header",
            ".lesson-item",
        ]
        missing = [cls for cls in required_classes if cls not in main_css]
        assert not missing, f"Missing outline tree classes: {missing}"

    def test_gen_log_styles(self, main_css):
        """main.css should include generation log component styles."""
        assert ".gen-log" in main_css, "Missing .gen-log class"


# ============================================================================
# Test: Navbar Consistency
# ============================================================================


class TestNavbarConsistency:
    """Verify navbar patterns are consistent across standalone pages."""

    @pytest.fixture
    def standalone_pages(self):
        """Pages that use standalone navbar (not sidebar).

        Note: session_player.html is excluded because it has unique UX requirements:
        - Users should use "End Session" button to exit (not direct dashboard link)
        - This allows proper session cleanup and progress tracking
        """
        pages = [
            "assessment_builder.html",
            "grading.html",
            "study_plan_builder.html",
            "course_designer.html",
            # session_player.html excluded - uses End Session button flow
        ]
        return [WEB_DIR / p for p in pages if (WEB_DIR / p).exists()]

    def test_no_dark_navbar(self, standalone_pages):
        """Standalone pages should not use dark navbar (bg-dark navbar-dark).

        Note: This test specifically checks the <nav> element only, not the entire page.
        Other elements (like terminal-style log headers) may legitimately use bg-dark.
        """
        failures = []
        for page in standalone_pages:
            content = page.read_text(encoding="utf-8")
            # Extract only the nav element to check
            nav_match = re.search(
                r"<nav[^>]*>.*?</nav>", content, re.DOTALL | re.IGNORECASE
            )
            if nav_match:
                nav_content = nav_match.group(0)
                if "navbar-dark" in nav_content or "bg-dark" in nav_content:
                    failures.append(page.name)

        assert not failures, f"Pages with dark navbar (should be light): {failures}"

    def test_has_back_to_dashboard_link(self, standalone_pages):
        """Standalone pages should have a link back to dashboard."""
        failures = []
        for page in standalone_pages:
            content = page.read_text(encoding="utf-8")
            if "dashboard.html" not in content:
                failures.append(page.name)

        assert not failures, f"Pages missing dashboard link: {failures}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
