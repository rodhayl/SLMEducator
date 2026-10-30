"""
Test security utilities
"""

from src.core.security_utils import (
    get_or_create_encryption_key,
    get_or_create_jwt_secret,
    sanitize_input,
    sanitize_prompt,
    validate_table_name,
    scrub_sensitive_data,
)


class TestEncryptionKeyPersistence:
    """Test encryption key persistence"""

    def test_encryption_key_generated_once(self, tmp_path, monkeypatch):
        """Test that encryption key is generated once and reused"""
        # Set up temporary security directory
        security_dir = tmp_path / ".slm_educator"
        monkeypatch.setattr("src.core.security_utils.SECURITY_DIR", security_dir)
        monkeypatch.setattr(
            "src.core.security_utils.ENCRYPTION_KEY_FILE",
            security_dir / "encryption.key",
        )

        # First call should generate key
        key1 = get_or_create_encryption_key()
        assert key1 is not None
        assert len(key1) > 0

        # Second call should return same key
        key2 = get_or_create_encryption_key()
        assert key1 == key2

    def test_encryption_key_from_env(self, monkeypatch):
        """Test that encryption key can be loaded from environment"""
        test_key = b"test_encryption_key_12345678901234567890123456789012"
        monkeypatch.setenv("SLM_ENCRYPTION_KEY", test_key.decode())

        key = get_or_create_encryption_key()
        assert key == test_key


class TestJWTSecretPersistence:
    """Test JWT secret persistence"""

    def test_jwt_secret_generated_once(self, tmp_path, monkeypatch):
        """Test that JWT secret is generated once and reused"""
        # Set up temporary security directory
        security_dir = tmp_path / ".slm_educator"
        monkeypatch.setattr("src.core.security_utils.SECURITY_DIR", security_dir)
        monkeypatch.setattr(
            "src.core.security_utils.JWT_SECRET_FILE", security_dir / "jwt.secret"
        )

        # First call should generate secret
        secret1 = get_or_create_jwt_secret()
        assert secret1 is not None
        assert len(secret1) > 20

        # Second call should return same secret
        secret2 = get_or_create_jwt_secret()
        assert secret1 == secret2

    def test_jwt_secret_from_env(self, monkeypatch):
        """Test that JWT secret can be loaded from environment"""
        test_secret = "test_jwt_secret_1234567890"
        monkeypatch.setenv("JWT_SECRET", test_secret)

        secret = get_or_create_jwt_secret()
        assert secret == test_secret


class TestInputSanitization:
    """Test input sanitization"""

    def test_sanitize_removes_control_characters(self):
        """Test that control characters are removed"""
        dirty = "Hello\x00World\x01Test"
        clean = sanitize_input(dirty)
        assert "\x00" not in clean
        assert "\x01" not in clean
        assert "HelloWorldTest" == clean

    def test_sanitize_preserves_newlines_and_tabs(self):
        """Test that newlines and tabs are preserved"""
        text = "Hello\nWorld\tTest"
        clean = sanitize_input(text)
        assert "\n" in clean
        assert "\t" in clean

    def test_sanitize_truncates_long_input(self):
        """Test that long input is truncated"""
        long_text = "A" * 20000
        clean = sanitize_input(long_text, max_length=1000)
        assert len(clean) == 1000

    def test_sanitize_prompt_allows_longer_text(self):
        """Test that prompt sanitization allows longer text"""
        long_text = "A" * 20000
        clean = sanitize_prompt(long_text)
        assert len(clean) == 20000


class TestTableNameValidation:
    """Test SQL injection prevention"""

    def test_valid_table_names(self):
        """Test that valid table names pass"""
        assert validate_table_name("users")
        assert validate_table_name("study_plans")
        assert validate_table_name("_internal_table")
        assert validate_table_name("Table123")

    def test_invalid_table_names(self):
        """Test that invalid table names fail"""
        assert not validate_table_name("users; DROP TABLE users--")
        assert not validate_table_name("users OR 1=1")
        assert not validate_table_name("123table")  # Can't start with number
        assert not validate_table_name("table-name")  # No hyphens
        assert not validate_table_name("")

    def test_sql_keywords_rejected(self):
        """Test that SQL keywords are rejected"""
        assert not validate_table_name("select")
        assert not validate_table_name("DROP")
        assert not validate_table_name("delete")


class TestSensitiveDataScrubbing:
    """Test sensitive data scrubbing"""

    def test_scrub_api_keys(self):
        """Test that API keys are scrubbed"""
        message = "Using api_key=sk-1234567890abcdef"
        scrubbed = scrub_sensitive_data(message)
        assert "sk-1234567890abcdef" not in scrubbed
        assert "api_key=***" in scrubbed

    def test_scrub_passwords(self):
        """Test that passwords are scrubbed"""
        message = "Login with password=MySecretPass123"
        scrubbed = scrub_sensitive_data(message)
        assert "MySecretPass123" not in scrubbed
        assert "password=***" in scrubbed

    def test_scrub_bearer_tokens(self):
        """Test that bearer tokens are scrubbed"""
        message = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        scrubbed = scrub_sensitive_data(message)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
        assert "Bearer ***" in scrubbed
