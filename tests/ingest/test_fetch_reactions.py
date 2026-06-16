import pytest
from pydantic import ValidationError

from ingest.fetch_reactions import GuardianClient

SAMPLE_RESULT = {
    "id": "football/2026/jun/11/argentina-mexico-world-cup-match-report",
    "type": "article",
    "sectionId": "football",
    "sectionName": "Football",
    "webPublicationDate": "2026-06-11T21:30:00Z",
    "webTitle": "Argentina ease past Mexico in their opener",
    "webUrl": "https://www.theguardian.com/football/2026/jun/11/argentina-mexico-world-cup-match-report",
    "fields": {
        "byline": "Barney Ronay",
        "bodyText": "Argentina began the defence of their crown with a composed win...",
    },
    "tags": [
        {"id": "tone/matchreports", "type": "tone", "webTitle": "Match reports"},
        {"id": "football/argentina", "type": "keyword", "webTitle": "Argentina"},
    ],
}

MATCH_ID = 537327


def test_maps_article():
    a = GuardianClient._to_article(SAMPLE_RESULT, MATCH_ID)
    assert a is not None
    assert a.id.endswith("match-report")
    assert a.match_id == MATCH_ID          
    assert a.source == "guardian"          
    assert a.title.startswith("Argentina")
    assert a.body.startswith("Argentina began")
    assert a.byline == "Barney Ronay"
    assert a.article_type == "matchreports" 
    assert a.url.startswith("https://")
    assert a.published.year == 2026


def test_skips_result_with_no_body():
    no_body = {**SAMPLE_RESULT, "fields": {"byline": "Someone"}}  
    assert GuardianClient._to_article(no_body, MATCH_ID) is None


def test_article_type_is_none_without_tone_tag():
    no_tone = {**SAMPLE_RESULT, "tags": [
        {"id": "football/argentina", "type": "keyword", "webTitle": "Argentina"},
    ]}
    a = GuardianClient._to_article(no_tone, MATCH_ID)
    assert a is not None
    assert a.article_type is None


def test_missing_required_field_fails_loud():
    incomplete = {k: v for k, v in SAMPLE_RESULT.items() if k != "webTitle"}
    with pytest.raises(KeyError):
        GuardianClient._to_article(incomplete, MATCH_ID)


def test_tone_helper():
    assert GuardianClient._tone([{"id": "tone/comment", "type": "tone"}]) == "comment"
    assert GuardianClient._tone([{"id": "football/spain", "type": "keyword"}]) is None
    assert GuardianClient._tone([]) is None