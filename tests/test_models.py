from counsel import llm, router


def test_plain_answer_hides_the_json_wrapper():
    assert router.plain('{"answer": "30 days", "actions": []}') == "30 days"
    assert router.plain('{"answer": "cut off mid-rep') == "cut off mid-rep"


class Tags:
    def json(self):
        names = ["qwen3:8b", "lfm3:1.7b", "llama3.2:3b", "lfm2.5:24b", "nomic-embed-text:latest", "lfm2.5:8b"]
        return {"models": [{"name": n} for n in names]}


def models(monkeypatch, key):
    monkeypatch.setattr(llm.httpx, "get", lambda *a, **k: Tags())
    monkeypatch.setattr(llm, "_models_cache", (0.0, []))
    if key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    else:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return llm.available_models()


def test_offers_every_chat_model_with_the_default_first(monkeypatch):
    assert models(monkeypatch, key=True) == ["lfm3:1.7b", "lfm2.5:8b", "llama3.2:3b", "qwen3:8b", llm.CLOUD_MODEL]


def test_stand_in_is_not_offered_when_it_is_playing_the_cloud(monkeypatch):
    assert models(monkeypatch, key=False) == ["lfm3:1.7b", "lfm2.5:8b", "llama3.2:3b"]
