
import pytest
from ingest.fetch_history import WikipediaClient, load_history_docs

PAGE = {
    "pageid": 12345,
    "ns": 0,
    "title": "Argentina national football team",
    "extract": "The Argentina national football team represents Argentina in "
    "men's international football and is a three-time World Cup winner.",
}
MISSING_PAGE = {"ns": 0, "title": "Some Nonexistent Page Xyz", "missing": True}
EMPTY_PAGE = {"pageid": 7, "ns": 0, "title": "Stub", "extract": ""}


def test_maps_page():
    doc = WikipediaClient._to_doc(PAGE)
    assert doc is not None
    assert doc.id == "12345"
    assert doc.source == "wikipedia"
    assert doc.title == "Argentina national football team"
    assert doc.body.startswith("The Argentina")
    assert doc.url == "https://en.wikipedia.org/wiki/Argentina_national_football_team"


def test_skips_missing_page():
    assert WikipediaClient._to_doc(MISSING_PAGE) is None


def test_skips_empty_extract():
    assert WikipediaClient._to_doc(EMPTY_PAGE) is None


def test_slug():
    assert WikipediaClient._slug("Lionel Messi") == "Lionel_Messi"
    assert WikipediaClient._slug("AC/DC") == "AC_DC"

def test_load_history_docs(tmp_path):
    f = tmp_path / "history.jsonl"
    f.write_text(
        '{"id": "a", "title": "T", "body": "B", "url": "http://e"}\n'
        "\n"  
        '{"id": "b", "title": "T2", "body": "B2"}\n'
    )
    docs = load_history_docs(f)
    assert len(docs) == 2
    assert all(d.source == "curated" for d in docs)
    assert docs[0].url == "http://e"
    assert docs[1].url is None
 
 
def test_load_history_docs_bad_json(tmp_path):
    f = tmp_path / "bad.jsonl"
    f.write_text('{"id": "a", "title": "T", "body": "B"}\n{nope}\n')
    with pytest.raises(ValueError):
        load_history_docs(f)
 
 
def test_load_history_docs_missing_field(tmp_path):
    f = tmp_path / "missing.jsonl"
    f.write_text('{"id": "a", "title": "T"}\n')
    with pytest.raises(ValueError):
        load_history_docs(f)
