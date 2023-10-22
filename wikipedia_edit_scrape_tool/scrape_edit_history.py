import ipdb
import bs4
import unicodedata
from dataclasses import dataclass
from typing import Dict, Any, List
import re
from datetime import datetime
import dateparser
import loguru
import requests

from .scrape_page_content import get_info
from .constants import TARGET_LANGUAGES

logger = loguru.logger

@dataclass
class WikipageSnapshot:
    edit_date: datetime
    edit_size: str 
    content: Dict[str, Any]
    editor: str

@dataclass
class EditMetadata:
    timestamp: str
    timestamp_href: str
    curr_size_bytes: str
    diff_bytes: str
    editor: str

def extract_edit_metadata(edit_li) -> EditMetadata:
    timestamp = edit_li.find('a', class_='mw-changeslist-date').text
    # also get the href so we can navigate to the snapshot of the page at that time.
    timestamp_href = edit_li.find('a', class_='mw-changeslist-date')['href']
    try:
        editor = edit_li.find('a', class_='mw-userlink')['href']
    except TypeError as e:
        # assert that the editor has been deleted.
        assert edit_li.find('span', class_='history-deleted') is not None
        editor = 'editor-deleted'

    curr_size = edit_li.find('span', class_='history-size mw-diff-bytes').text # bytes might be written in a different language. and possibly the numbers also

    # diff_bytes = edit_li.find('span', class_='mw-diff-bytes ').text
    # depending on whether content was added, removed, or stayed th same, the class will be 'mw-plusminus-pos', 'mw-plusminus-neg', or 'mw-plusminus-null'.
    # look for the span with class 'mw-plusminus-null', 'mw-plusminus-pos', or 'mw-plusminus-neg'
    # code:
    def _find_diff_bytes():
        # assert edit_li.find('span', class_='mw-plusminus-pos') or edit_li.find('span', class_='mw-plusminus-neg') or edit_li.find('span', class_='mw-plusminus-null') or \
        # do the assertion but search for strong and span
        assert edit_li.find('strong', class_='mw-plusminus-pos') or edit_li.find('strong', class_='mw-plusminus-neg') or edit_li.find('strong', class_='mw-plusminus-null') or \
            edit_li.find('span', class_='mw-plusminus-pos') or edit_li.find('span', class_='mw-plusminus-neg') or edit_li.find('span', class_='mw-plusminus-null')
        # candidate_plus_minus_spans = [edit_li.find('span', class_='mw-plusminus-pos'), edit_li.find('span', class_='mw-plusminus-neg'), edit_li.find('span', class_='mw-plusminus-null')]
        candidate_plus_minus_spans = [edit_li.find('strong', class_='mw-plusminus-pos'), edit_li.find('strong', class_='mw-plusminus-neg'), edit_li.find('strong', class_='mw-plusminus-null'), \
            edit_li.find('span', class_='mw-plusminus-pos'), edit_li.find('span', class_='mw-plusminus-neg'), edit_li.find('span', class_='mw-plusminus-null')]
        plus_minus_span = [span for span in candidate_plus_minus_spans if span][0]
        diff_bytes = plus_minus_span.text
        return diff_bytes 
    return EditMetadata(timestamp, timestamp_href, curr_size, _find_diff_bytes(), editor)

def get_edit_history_metadata(base_lang_url, lang_wiki_id) -> List[EditMetadata]:
    """Obtain all edits for person at {page_title}.

    Returns:
        List[Tuple[str, str, str]]: A list of tuples containing the timestamp, timestamp href, and diff bytes for each edit.

    TODO: The contributing user can also be obtained here.
    """
    url = f"https://{base_lang_url}/w/index.php?title={lang_wiki_id}&action=history"
    #  https://ru.wikipedia.org/w/index.php?title=%D0%9A%D1%83%D0%BA,_%D0%A2%D0%B8%D0%BC&action=history
    # 
    response = requests.get(url)
    assert response.status_code == 200
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    navigation_bar =soup.find('div', class_="mw-pager-navigation-bar")
    if navigation_bar: # doesn't exist for people who only have a few edits
        # get the last mw-numlink in the navigation bar
        last_numlink = navigation_bar.find_all('a', class_='mw-numlink')[-1]
        # get the href of the most number of elements to display, then go to that page.
        last_numlink_text = last_numlink.text # will be a number
        last_numlink_href = last_numlink['href']
        last_numlink_url = f"https://{base_lang_url}{last_numlink_href}"
        response = requests.get(last_numlink_url)
        soup = bs4.BeautifulSoup(response.content, 'html.parser')
    
    # get the link to the next N elements, if it exists. It will be in an anchor tag with class "mw-nextlink".
    metadata_all_edits = []

    # Find the edit history table
    # get the section with id "pagehistory". It is in a <section> tag.
    num_edits = 0

    def _get_older_text(base_lang_url):
        if base_lang_url == "en.wikipedia.org":
            return "older" 
        elif base_lang_url == "ko.wikipedia.org":
            return "이전"
        elif base_lang_url == "fr.wikipedia.org":
            return "plus anciennes"
        elif base_lang_url == "es.wikipedia.org":
            return "anteriores"
        elif base_lang_url == "ru.wikipedia.org":
            return "более старых"
        elif base_lang_url == "ko.wikipedia.org":
            return "이전"
        else:
            raise ValueError(f"Language {base_lang_url} not supported.")

    while True:
        page_history_section = soup.find('section', id='pagehistory')
        history_tables = page_history_section.find_all('ul', class_='mw-contributions-list')
        for table in history_tables:
            # iterate through <li> tags in the table.
            for li in table.find_all('li'):
                # get the anchor with class "mw-changeslist-date" and get the text.
                if not li.find('a', class_='mw-changeslist-date'):
                    continue
                edit_metadata = extract_edit_metadata(li)
                metadata_all_edits.append(edit_metadata)
                num_edits += 1
                if num_edits % 1000 == 0:
                    print(f"Scraped {num_edits} edits") 

        next_links = soup.find_all('a', class_='mw-nextlink')
        assert len(next_links) == 2 or len(next_links) == 0
        if len(next_links) == 0:
            break
        else:
            next_link = next_links[0]
            # assert next_link.text == f"older {last_numlink_text}", ipdb.set_trace()
            assert f"{_get_older_text(base_lang_url)}" in next_link.text and f"{last_numlink_text}" in next_link.text, ipdb.set_trace()
            next_link_href = next_link['href']
            next_link_url = f"https://{base_lang_url}{next_link_href}"
            response = requests.get(next_link_url)
            soup = bs4.BeautifulSoup(response.content, 'html.parser')
    return metadata_all_edits

def get_multilingual_wikilinks_mediawiki(en_wiki_id, wiki_languages=TARGET_LANGUAGES):
    response = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&prop=langlinks&titles={en_wiki_id}&format=json")
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": en_wiki_id,
        "prop": "langlinks",
        "lllimit": 500,
        "format": "json",
    }
    lang_to_wikilinks = {}
    lang_to_wikilinks['enwiki'] = f"https://en.wikipedia.org/wiki/{en_wiki_id}"

    response = requests.get(url, params=params).json()
    page_id = list(response["query"]["pages"].keys())[0]
    try:
        langlinks = response["query"]["pages"][page_id]["langlinks"]
        lang_to_wikilang = {
            'ko': 'kowiki',
            'fr': 'frwiki',
            'es': 'eswiki',
            'ru': 'ruwiki',
            'en': 'enwiki'
        }
        # filter items in the dictionary that aren't a value in the lang_to_wikilang dictionary
        lang_to_wikilang = {k: v for k, v in lang_to_wikilang.items() if v in wiki_languages}

        for item in langlinks:
            wiki_id = item["*"].replace(" ", "_")
            if item["lang"] not in lang_to_wikilang:
                continue
            lang_to_wikilinks[lang_to_wikilang[item["lang"]]] = f"https://{item['lang']}.wikipedia.org/wiki/{wiki_id}"
    except KeyError as e:
        logger.warning(f"Could not find wikilinks for {en_wiki_id} through mediawiki API.")

    def _add_spanish_link_manual():
        # the spanish link should be the same but with "es" instead of "en". But we should check that the link is valid.
        # if it's not, don't add it.
        spanish_link = f"https://es.wikipedia.org/wiki/{en_wiki_id}"
        response = requests.get(spanish_link)
        if response.status_code == 200:
            lang_to_wikilinks['eswiki'] = spanish_link
        else:
            logger.warning(f"Could not find Spanish link for {en_wiki_id}")

    def _add_french_link_manual():
        french_link = f"https://fr.wikipedia.org/wiki/{en_wiki_id}"
        response = requests.get(french_link)
        if response.status_code == 200:
            lang_to_wikilinks['frwiki'] = french_link
        else:
            logger.warning(f"Could not find French link for {en_wiki_id}")
    if ('eswiki' not in lang_to_wikilinks) and ('eswiki' in wiki_languages):
        _add_spanish_link_manual()
    if ('frwiki' not in lang_to_wikilinks) and ('frwiki' in wiki_languages):
        _add_french_link_manual()
    
    return lang_to_wikilinks

def get_edit_history_metadata_all_languages(en_wiki_id, target_languages=TARGET_LANGUAGES):
    # lang_to_site_link = get_multilingual_wikilinks(en_wiki_id, target_languages)
    lang_to_site_link = get_multilingual_wikilinks_mediawiki(en_wiki_id, target_languages)
    print(lang_to_site_link)
    lang_to_edit_metadata = {} 
    try:
        assert len(lang_to_site_link) != 0
    except AssertionError as e:
        logger.error(f"Could not obtain *any* of the multilingual sitelinks for {en_wiki_id}")
        return lang_to_edit_metadata

    try:
        for lang, sitelink in lang_to_site_link.items(): # of the form: https://es.wikipedia.org/wiki/Tim_Cook
            # get the base url, e.g., es.wikipedia.org
            # get the wiki id (e.g., Tim_Cook)
            base_lang_url = sitelink.split("/")[2]
            lang_wiki_id = sitelink.split("/")[-1] # assuming there are no / in the wiki id
            edit_metadata = get_edit_history_metadata(base_lang_url, lang_wiki_id)
            print(f"Completed scraping edit history for {lang}")
            lang_to_edit_metadata[lang] = edit_metadata
    except AttributeError:
        ipdb.set_trace()
    return lang_to_edit_metadata

def parse_wikipedia_korean_datetime_format(wiki_format_date: str) -> datetime:
    """Parse the date format used in the revision histories for the Korean version of Wikipedia 
    (e.g., https://ko.wikipedia.org/w/index.php?title=%ED%8C%80_%EC%BF%A1&action=history).

    Args:
        wiki_format_date (str): Date from wikipedia revision history.
    
    Examples:
    >>> parse_wikipedia_korean_datetime_format("2020년 12월 31일 (목) 22:59")
    datetime.datetime(2020, 12, 31, 22, 59)

    Returns:
        datetime.datetime: Datetime object with year, month, day, hour, and minute.
    """
    # create a regex to parse the date format. use spaces to split the string.
    kdate_re = re.compile(r"(\d+)[^0-9]\s(\d+)[^0-9]\s(\d+)[^0-9] \(\w+\) (\d+):(\d+)")
    match = kdate_re.match(wiki_format_date)
    # create a datetime object from the parsed date.
    year, month, day, hour, minute = match.groups()
    return datetime(int(year), int(month), int(day), int(hour), int(minute))

def parse_revision_date(revision_date_str: str, lang_wiki: str) -> datetime:
    if lang_wiki != "kowiki":
        return dateparser.parse(revision_date_str)
    else:
        return parse_wikipedia_korean_datetime_format(revision_date_str)

def _get_base_url_for_language(lang_wiki: str):
    if lang_wiki == "enwiki":
        return "en.wikipedia.org"
    elif lang_wiki == "frwiki":
        return "fr.wikipedia.org"
    elif lang_wiki == "kowiki":
        return "ko.wikipedia.org"
    elif lang_wiki == "eswiki":
        return "es.wikipedia.org"
    elif lang_wiki == "ruwiki":
        return "ru.wikipedia.org"
    else:
        raise ValueError(f"Language {lang_wiki} not supported.")

def convert_edit_diff_to_int(diff_bytes: str) -> int:
    diff_bytes_unpolarized = diff_bytes
    if diff_bytes_unpolarized.startswith("+"):
        diff_bytes_unpolarized = diff_bytes[1:]
    elif diff_bytes_unpolarized.startswith("-") or diff_bytes_unpolarized.startswith("−"):
        diff_bytes_unpolarized = diff_bytes[1:]
    try:
        cleaned_string = unicodedata.normalize('NFKD', diff_bytes_unpolarized).encode('ascii', 'ignore').decode('utf-8')
        return int(cleaned_string.replace(" ", "").replace(",", ""))
    except ValueError as e:
        ipdb.set_trace()

def get_snapshot_for_metadata(edit_metadata: EditMetadata, lang_wiki):
    page_link = f"https://{_get_base_url_for_language(lang_wiki)}" + edit_metadata.timestamp_href
    page_info = get_info(page_link, lang_wiki)
    page_date = parse_revision_date(edit_metadata.timestamp, lang_wiki)
    page_size = edit_metadata.curr_size_bytes
    return WikipageSnapshot(page_date, page_size, page_info, edit_metadata.editor)

def get_edit_history_for_language(lang_wiki: str, edit_metadata_list: List[EditMetadata]) -> List[WikipageSnapshot]:
    logger.info(f"Started scraping edit history for {lang_wiki}")
    initial_page_edit = edit_metadata_list[0]
    initial_page_size = initial_page_edit.diff_bytes
    initial_page_link = f"https://{_get_base_url_for_language(lang_wiki)}" + initial_page_edit.timestamp_href
    initial_page_info = get_info(initial_page_link, lang_wiki)
    initial_page_date = parse_revision_date(initial_page_edit.timestamp, lang_wiki)

    weekly_snapshots = [WikipageSnapshot(initial_page_date, 
                                         initial_page_size, 
                                         initial_page_info,
                                         initial_page_edit.editor)]

    week_edit_size = 0
    # import dateparser.parse('22:59 28 dic 2022')
    current_date = initial_page_date
    for edit_metadata in (edit_metadata_list[1:]):
        edit_date = parse_revision_date(edit_metadata.timestamp, lang_wiki)
        num_days_between = (edit_date - current_date).days

        if num_days_between >= 30:
            # save the snapshot
            week_edit_size += convert_edit_diff_to_int(edit_metadata.diff_bytes)
            weekly_snapshots.append(WikipageSnapshot(edit_date, 
                                    week_edit_size, 
                                    get_info(f"https://{_get_base_url_for_language(lang_wiki)}" + edit_metadata.timestamp_href, lang_wiki),
                                    edit_metadata.editor))
            week_edit_size = 0
            current_date = edit_date
        else:
            week_edit_size += convert_edit_diff_to_int(edit_metadata.diff_bytes)
    logger.info(f"Completed scraping edit history for {lang_wiki}")
    return weekly_snapshots

def get_edit_history(en_wiki_id: str, target_languages=TARGET_LANGUAGES) -> Dict[str, Any]:
    """_summary_

    Args:
        en_wiki_id (str): Wikipedia ID.

    Returns:
        Dict[str, Any]: A dictionary containing the edit history metadata and snapshots for each language.
    
    Examples:
    >>> get_edit_history("Tim_Cook", ["enwiki", "frwiki", "eswiki", "ruwiki", "kowiki"]])
    """
    person_info = {}

    edit_history_metadata_all_languages = get_edit_history_metadata_all_languages(en_wiki_id, target_languages) 
    person_info["edit_history_metadata_all_languages"] = edit_history_metadata_all_languages
    edit_history_all_languages = {}

    logger.info(f"Working on scraping edit history for {en_wiki_id}")
    for lang_wiki, metadata_edit_history in edit_history_metadata_all_languages.items():
        metadata_edit_history_date_ascending = list(reversed(metadata_edit_history))
        snapshots_edit_history = get_edit_history_for_language(lang_wiki, metadata_edit_history_date_ascending)
        edit_history_all_languages[lang_wiki] = snapshots_edit_history
    logger.info(f"Completed scraping edit history for {en_wiki_id}")
    person_info["edit_history_snapshots_all_languages"] = edit_history_all_languages
    return person_info