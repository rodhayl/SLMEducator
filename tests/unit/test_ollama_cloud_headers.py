"""Export compatibility fix: never forward an environment key to other hosts."""
import pytest
from src.core.services.ai_service import AIService

@pytest.mark.parametrize('endpoint', ['https://ollama.com','https://ollama.com/','https://ollama.com:443'])
def test_official_cloud_uses_ephemeral_key(monkeypatch, endpoint):
    monkeypatch.setenv('OLLAMA_API_KEY','synthetic-not-a-real-key')
    service = AIService.__new__(AIService)
    assert service._ollama_cloud_headers(endpoint) == {'Authorization':'Bearer synthetic-not-a-real-key'}

@pytest.mark.parametrize('endpoint', ['http://ollama.com','http://localhost:11434','https://ollama.com.example.invalid','https://example.invalid','https://user@ollama.com','https://ollama.com:8443'])
def test_environment_key_not_forwarded_elsewhere(monkeypatch, endpoint):
    monkeypatch.setenv('OLLAMA_API_KEY','synthetic-not-a-real-key')
    assert AIService.__new__(AIService)._ollama_cloud_headers(endpoint) == {}

def test_missing_environment_key(monkeypatch):
    monkeypatch.delenv('OLLAMA_API_KEY',raising=False)
    assert AIService.__new__(AIService)._ollama_cloud_headers('https://ollama.com') == {}
