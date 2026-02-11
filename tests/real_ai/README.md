# Real AI Test Suite
# ===================

"""
This directory contains tests that use REAL AI/LLM services.

⚠️  CRITICAL WARNINGS:
- These tests make ACTUAL API calls to real LLM providers
- These tests will COST MONEY (token usage)
- These tests are SLOW (network latency, AI processing time)
- These tests require VALID API credentials configured

## Strict Rules

### ❌ FORBIDDEN:
1. NO mocks (`unittest.mock`, `pytest-mock`, etc.)
2. NO fakes
3. NO stubs
4. NO simulation of AI responses

### ✅ REQUIRED:
1. Use ONLY real AIService instances
2. Make ACTUAL API calls
3. Verify REAL LLM responses
4. Test with configured AI provider (from settings.properties)

## Configuration

Tests use AI configuration from `settings.properties`:
- Provider (e.g., openrouter, openai)
- Model (e.g., openrouter/sherlock-dash-alpha)
- API Key (encrypted)

## Running Tests

```bash
# Run all real AI tests
pytest tests/real_ai/ -v -s

# Run with token usage reporting
pytest tests/real_ai/ -v -s --tb=short

# Run specific test
pytest tests/real_ai/test_real_ai_integration.py::TestRealAIIntegration::test_real_ai_simple_generation -v -s
```

Or use the dedicated runner:
```bash
.\run_tests_real_ai.bat
```

## Test Structure

### conftest.py
- Enforces strict no-mock policy
- Validates before/after each test
- Provides `real_ai_service` fixture (actual AI service)
- Auto-marks all tests as `real_ai`, `no_mock`, `slow`

### test_real_ai_integration.py
- Basic AI functionality tests
- Tutoring with context tests
- Grading tests
- End-to-end workflow tests

## Cost Considerations

Each test run will consume tokens:
- Simple generation: ~50-100 tokens
- Tutoring: ~200-500 tokens
- Full suite: ~2000-5000 tokens

**Estimate:** $0.01 - $0.10 per full test run (varies by provider)

## When to Run

❌ **DON'T run on every commit** - too expensive

✅ **DO run:**
- Before major releases
- When changing AI integration code
- When updating AI providers
- Weekly validation of production AI
- After AI service refactoring

## Expected Behavior

- Tests are **SLOW** (5-30 seconds each)
- Tests **COST MONEY**
- Tests may **FAIL** due to:
  - Network issues
  - API rate limits
  - Invalid API keys
  - Provider outages
  - LLM response variability

## Debugging Failed Tests

If tests fail:

1. **Check API credentials** in settings.properties
2. **Verify network connection**
3. **Check provider status** (openrouter.ai, openai.com)
4. **Review token limits** - may have hit rate limit
5. **Check response** - LLMs are non-deterministic

## Adding New Tests

When adding tests to this suite:

```python
def test_my_real_ai_feature(real_ai_service, test_user):
    """
    Brief description
    
    Makes ACTUAL API call - costs tokens!
    """
    # NO MOCKS ALLOWED - use real_ai_service fixture
    result = real_ai_service.some_method(...)
    
    # Verify real response
    assert result is not None
    assert not hasattr(result, '_mock_name')  # Ensure not a mock
    
    print(f"✅ Real AI test passed")
```

## Markers

All tests in this directory are automatically marked:
- `@pytest.mark.real_ai` - Uses real AI
- `@pytest.mark.no_mock` - Forbids mocking
- `@pytest.mark.slow` - Takes significant time

## Enforcement

The `conftest.py` enforces:
1. **Before each test:** Checks no mock libraries imported
2. **During each test:** Auto-fails if `unittest.mock` detected
3. **After each test:** Verifies no mocks were created
4. **Test collection:** Auto-marks all tests appropriately

**Violation = Immediate test failure**

Example error:
```
❌ MOCK USAGE DETECTED: unittest.mock was imported during test execution!
Real AI tests are strictly forbidden from using mocks.
```

---

**Remember:** These tests validate that your AI integration works in PRODUCTION with REAL LLMs. They are expensive but critical for confidence in deployment.
