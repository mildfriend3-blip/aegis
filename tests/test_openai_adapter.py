"""The live-model adapter: it must survive a rate-limited provider.

A free tier will answer 429, and a run that is already half done must not die on
it. These tests pin the retry behaviour without touching the network.
"""
import io
import json
import urllib.error

from aegis.targets import openai_agent


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _payload(content="ok", tool_calls=None):
    return {"choices": [{"message": {"content": content,
                                     "tool_calls": tool_calls or []}}]}


def test_adapter_retries_on_rate_limit(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "rate limited", {}, None)
        return _FakeResponse(json.dumps(_payload()).encode())

    monkeypatch.setattr(openai_agent.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(openai_agent.time, "sleep", lambda _s: None)  # don't really wait

    run = openai_agent.OpenAIAgent(api_key="test-key").run("hello", [])
    assert calls["n"] == 2          # retried once, then succeeded
    assert run.final_response == "ok"


def test_adapter_gives_up_on_a_non_retryable_error(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 401, "unauthorised", {}, None)

    monkeypatch.setattr(openai_agent.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(openai_agent.time, "sleep", lambda _s: None)

    try:
        openai_agent.OpenAIAgent(api_key="bad").run("hello", [])
        assert False, "should have raised"
    except urllib.error.HTTPError as exc:
        assert exc.code == 401
    assert calls["n"] == 1          # a 401 is not retried


def test_adapter_requires_a_key(monkeypatch):
    monkeypatch.delenv("AEGIS_OPENAI_API_KEY", raising=False)
    try:
        openai_agent.OpenAIAgent(api_key="").run("hello", [])
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "AEGIS_OPENAI_API_KEY" in str(exc)
