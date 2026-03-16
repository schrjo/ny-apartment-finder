import notifier


class DummyResponse:
    def raise_for_status(self):
        return None


def test_telegram_sends_per_listing(monkeypatch):
    calls = []
    sleep_calls = []

    def fake_post(url, data=None, timeout=None, json=None):
        calls.append((url, data, timeout))
        return DummyResponse()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setenv("TELEGRAM_DELAY", "0")
    monkeypatch.setattr(notifier.requests, "post", fake_post)
    monkeypatch.setattr(notifier.time, "sleep", lambda s: sleep_calls.append(s))

    listings = [
        {"id": "a", "title": "Apt A", "url": "https://a", "source": "src1", "price": "$1000"},
        {"id": "b", "title": "Apt B", "url": "https://b", "source": "src2"},
    ]

    notifier.notify(listings)

    assert len(calls) == 2
    for call, listing in zip(calls, listings):
        url, payload, timeout = call
        assert url == "https://api.telegram.org/bottest-token/sendMessage"
        assert payload["chat_id"] == "123456"
        assert payload["parse_mode"] == "HTML"
        assert payload["disable_web_page_preview"] is True
        assert listing["title"] in payload["text"]
        assert listing["url"] in payload["text"]
        assert timeout == 10

    assert sleep_calls == []


def test_telegram_failure_falls_back_to_stdout(monkeypatch, capsys):
    def fake_post(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setenv("TELEGRAM_DELAY", "0")
    monkeypatch.setattr(notifier.requests, "post", fake_post)

    notifier.notify([{"id": "a", "title": "Apt A", "url": "https://a", "price": "$999"}])
    captured = capsys.readouterr()

    assert "Telegram send failed" in captured.out
    assert "NEW LISTING:" in captured.out
    assert "Apt A" in captured.out


def test_telegram_sends_to_multiple_chat_ids(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None, json=None):
        calls.append((url, data, timeout))
        return DummyResponse()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111,222")
    monkeypatch.setenv("TELEGRAM_DELAY", "0")
    monkeypatch.setattr(notifier.requests, "post", fake_post)

    listings = [
        {"id": "a", "title": "Apt A", "url": "https://a", "source": "src"},
        {"id": "b", "title": "Apt B", "url": "https://b", "source": "src"},
    ]

    notifier.notify(listings)

    assert len(calls) == 4
    chat_ids = [payload["chat_id"] for _, payload, _ in calls]
    assert chat_ids.count("111") == 2
    assert chat_ids.count("222") == 2


def test_fallback_prints_without_telegram(capsys, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    notifier.notify([{"id": "a", "title": "Apt A", "url": "https://a"}])
    captured = capsys.readouterr()

    assert "NEW LISTING:" in captured.out
    assert "Apt A" in captured.out
