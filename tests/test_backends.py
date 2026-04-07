"""Tests for backend routing."""

from promptclimb.backends import call_model as route_call


def test_ollama_routing(monkeypatch):
    """Verify ollama: prefix routes to ollama backend."""
    called_with = {}

    def mock_call(prompt, model, temperature=0.0, max_tokens=1024):
        called_with["model"] = model
        return "mocked"

    import promptclimb.backends.ollama as ollama_mod
    monkeypatch.setattr(ollama_mod, "call_model", mock_call)

    result = route_call("test", "ollama:llama3.2")
    assert result == "mocked"
    assert called_with["model"] == "ollama:llama3.2"


def test_openai_routing(monkeypatch):
    """Verify openai: prefix routes to openai backend."""
    called_with = {}

    def mock_call(prompt, model, temperature=0.0, max_tokens=1024):
        called_with["model"] = model
        return "mocked"

    import promptclimb.backends.openai as openai_mod
    monkeypatch.setattr(openai_mod, "call_model", mock_call)

    result = route_call("test", "openai:gpt-4o-mini")
    assert result == "mocked"
    assert called_with["model"] == "openai:gpt-4o-mini"


def test_http_routing(monkeypatch):
    """Verify http:// URLs route to openai backend."""
    called_with = {}

    def mock_call(prompt, model, temperature=0.0, max_tokens=1024):
        called_with["model"] = model
        return "mocked"

    import promptclimb.backends.openai as openai_mod
    monkeypatch.setattr(openai_mod, "call_model", mock_call)

    result = route_call("test", "http://localhost:8082")
    assert result == "mocked"
