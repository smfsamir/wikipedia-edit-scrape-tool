import ipdb
import pytest

from wikipedia_edit_scrape_tool.scrape_page_content import get_text, clean_paragraph, Paragraph

# from wikipedia_edit_scrape_tool.scrape_page_content import get_multilingual_wikilinks_mediawiki

def test_paragraphs_delineated_en():
    person_id = 'Ellen_DeGeneres'
    en_link = f"https://en.wikipedia.org/wiki/{person_id}"
    content = get_text(en_link, 'enwiki')
    assert len(content) > 30

def test_paragraphs_delineated_fr():
    person_id = 'Ellen_DeGeneres'
    fr_link = f"https://fr.wikipedia.org/wiki/{person_id}"
    content = get_text(fr_link, 'frwiki')
    print(content[0])
    print(content[1])
    ipdb.set_trace()
    assert len(content) > 30

def test_clean_paragraph():
    paragraph = '**Ellen Lee DeGeneres** (/dəˈdʒɛnərəs/ _də- JEN-ər-əs_; born January 26,\n1958)[1][2] is an American comedian, television host, actress, and writer. She\nstarred in the sitcom _Ellen_ from 1994 to 1998, which earned her a Primetime\nEmmy Award for "The Puppy Episode". She also hosted the syndicated television\ntalk show, _The Ellen DeGeneres Show_ from 2003 to 2022, for which she\nreceived 33 Daytime Emmy Awards.\n\n'
    cleaned_summary_paragraph = clean_paragraph(paragraph)
    assert "(/dəˈdʒɛnərəs/ _də- JEN-ər-əs_; born January 26,\n1958)" not in cleaned_summary_paragraph
    assert "[1][2]" not in cleaned_summary_paragraph
    # assert that there are no \n, unless it's for starting a new paragraph (i.e., \n\n at the end of a paragraph)
    assert "\n" not in cleaned_summary_paragraph[:-2]

# TODO: use this to merge block quotes with the paragraph that they are part of
def test_alan_turing_paragraphs():
    person_id = 'Alan_Turing'
    en_link = f"https://en.wikipedia.org/wiki/{person_id}"
    content = get_text(en_link, 'enwiki')
    # get the text of the paragraph that says 'Alexander wrote of Turing's contribution:'
    turing_cont_paragraph = [p for p in content if isinstance(p, Paragraph) and 'Alexander wrote of Turing\'s contribution:' in p.clean_text][0]
    print(turing_cont_paragraph.clean_text)
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    print(content[2])

def test_caroline_mecary_paragraphs():
    person_id = 'Caroline_Mécary'
    fr_link = f"https://fr.wikipedia.org/wiki/{person_id}"
    content = get_text(fr_link, 'frwiki')
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    ipdb.set_trace()