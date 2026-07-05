from models import SearchResult
from pipeline import query


def _r(id, text, **meta):
    return SearchResult(id=id, text=text, metadata=meta, distance=0.1)


def test_build_context_numbers_unique_sources():
    results = [
        _r("match-537351", "Germany beat Curaçao 7-1...", layer="match"),
        _r("guardian-abc#0", "Havertz ruthless...", layer="reaction"),
    ]
    ctx, sources = query.build_context(results)
    assert ctx.startswith("[1] Germany beat Curaçao 7-1")
    assert "[2] Havertz ruthless" in ctx
    assert [s["n"] for s in sources] == [1, 2]


def test_build_context_dedupes_chunks_of_one_source():
    results = [
        _r("guardian-abc#0", "First chunk.", layer="reaction", title="T", url="u"),
        _r("guardian-abc#1", "Second chunk.", layer="reaction", title="T", url="u"),
        _r("match-537351", "Germany beat Curaçao 7-1.", layer="match"),
    ]
    ctx, sources = query.build_context(results)
    assert len(sources) == 2
    assert "[1] First chunk. Second chunk." in ctx
    assert sources[1]["n"] == 2


def test_format_source_line_match_has_no_url():
    line = query.format_source_line(1, {
        "layer": "match", "home": "Germany", "away": "Curaçao",
        "utc_date": "2026-06-14T16:00:00+00:00",
    })
    assert line == "[1] Match record: Germany vs Curaçao, 14 Jun 2026"
    assert "http" not in line


def test_format_source_line_guardian_has_title_and_url():
    line = query.format_source_line(2, {
        "layer": "reaction", "source": "guardian",
        "title": "Havertz and ruthless Germany show no mercy",
        "url": "https://theguardian.com/x",
    })
    assert line == ('[2] Guardian — "Havertz and ruthless Germany show no mercy" '
                    "— https://theguardian.com/x")


def test_format_source_line_history_without_url_omits_dash():
    line = query.format_source_line(3, {
        "layer": "history", "source": "wikipedia",
        "title": "Germany national football team",
    })
    assert line == '[3] Wikipedia — "Germany national football team"'


def test_build_messages_has_system_and_embeds_context():
    msgs = query.build_messages("Who won?", "[1] X beat Y.")
    assert msgs[0]["role"] == "system"
    assert "cite" in msgs[0]["content"].lower()
    assert msgs[1]["role"] == "user"
    assert "[1] X beat Y." in msgs[1]["content"]
    assert "Who won?" in msgs[1]["content"]


def test_answer_streams_and_appends_sources(monkeypatch, capsys):
    monkeypatch.setattr(query, "retrieve", lambda q, k: [
        _r("match-537351", "Germany beat Curaçao 7-1.", layer="match",
           home="Germany", away="Curaçao", utc_date="2026-06-14T16:00:00+00:00"),
    ])
    monkeypatch.setattr(query, "_stream_chat",
                        lambda m, model, stream=True: iter(["Germany ", "won [1]."]))

    out = query.answer("How did Germany do?")
    captured = capsys.readouterr().out
    assert out == "Germany won [1]."
    assert "Germany won [1]." in captured
    assert "Sources" in captured
    assert "[1] Match record: Germany vs Curaçao, 14 Jun 2026" in captured


def test_answer_handles_empty_retrieval(monkeypatch, capsys):
    monkeypatch.setattr(query, "retrieve", lambda q, k: [])
    out = query.answer("nonsense")
    assert out == ""
    assert "No matching context" in capsys.readouterr().out