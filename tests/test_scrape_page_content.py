import pytest

from wikipedia_edit_scrape_tool.scrape_page_content import get_text
from wikipedia_edit_scrape_tool.scrape_page_content import get_multilingual_wikilinks_mediawiki

def test_paragraphs_delineated():
    person_id = 'Ellen_DeGeneres'
    content = get_text(person_id, 'enwiki')
    en_link = f"https://en.wikipedia.org/wiki/{person_id}"

    summary_paragraph = snapshot.content[1]['section-text']['second'][0][1]
    summary_para_sents = sent_tokenize(summary_paragraph)
    all_facts = []
    for sentence in summary_para_sents:
        generated_facts = ask_gpt_for_facts(sentence)
        all_facts.append(generated_facts)
    all_facts_extracted = [response['choices'][0]['message']['content'] for response in all_facts]
    return all_facts_extracted

def test_all_content_extracted():