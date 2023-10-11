import pytest
from wikipedia_edit_scrape_tool.scrape_edit_history import get_edit_history, get_edit_history_metadata, get_edit_history_metadata_all_languages, parse_wikipedia_korean_datetime_format, convert_edit_diff_to_int
from wikipedia_edit_scrape_tool.scrape_edit_history import WikipageSnapshot
from wikipedia_edit_scrape_tool.edit_history_utils import get_last_snapshot, get_categories

# create a fixture for the edit history object
@pytest.fixture
def sample_edit_history_object_english_only():
    person_id = "Scottie_Barnes"
    weekly_snapshots = get_edit_history(person_id, ["enwiki"])
    return weekly_snapshots

def test_get_last_snapshot(sample_edit_history_object_english_only):
    last_snapshot = get_last_snapshot(sample_edit_history_object_english_only, "enwiki")
    assert type(last_snapshot) == WikipageSnapshot

def test_get_categories(sample_edit_history_object_english_only):
    last_snapshot = get_last_snapshot(sample_edit_history_object_english_only, "enwiki")
    assert "Living people" in get_categories(last_snapshot)

def test_get_edit_history():
    person_id = "Scottie_Barnes"
    weekly_snapshots = get_edit_history(person_id)

def test_get_edit_history_all_languages():
    person_id = "Scottie_Barnes"
    lang_to_metadata = get_edit_history_metadata_all_languages(person_id)

    assert len(lang_to_metadata['enwiki']) > len(lang_to_metadata['frwiki'])
    # print the lengths of the edit histories for each language
    for lang, metadata in lang_to_metadata.items():
        print(f"{lang}: {len(metadata)}")

def test_get_edit_history_w_korean():
    person_id = "Jennie_(singer)"
    weekly_snapshots = get_edit_history(person_id, TARGET_LANGUAGES)

def test_get_edit_history_3():
    person_id = "John_Alcorn_(singer)"
    weekly_snapshots = get_edit_history(person_id, TARGET_LANGUAGES)

def test_get_edit_history_metadata():
    history_metadata = get_edit_history_metadata("en.wikipedia.org", "Scottie_Barnes")
    assert history_metadata[0].diff_bytes == '+43'

def test_parse_wikipedia_korean_datetime_format():
    assert parse_wikipedia_korean_datetime_format('2021년 9월 5일 (일) 04:09') == datetime(2021, 9, 5, 4, 9)

def test_convert_edit_diff_to_int():
    assert convert_edit_diff_to_int('+43') == 43
    assert convert_edit_diff_to_int('-43') == 43
    assert convert_edit_diff_to_int('0') == 0