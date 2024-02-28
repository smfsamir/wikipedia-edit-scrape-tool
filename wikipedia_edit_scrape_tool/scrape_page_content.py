import loguru
import ipdb
from urllib.parse import urlparse, parse_qs
import bs4
import requests
from requests_html import HTMLSession
import re
# import dataclasses
from nltk.tokenize import sent_tokenize
from typing import Dict, Union, List
from dataclasses import dataclass
from html2text import HTML2Text
import os
from .wiki_regexes import cut_list, cut_sup, cut_note, cut_table, cut_first_table,\
    cut_references2, cut_references, cut_references_es, cut_references_fr, cut_references_fr2, cut_references_ko, cut_references_ru,\
          double_paren, emphasis, bold, second_heading, third_heading, fourth_heading, second_heading_separation, fourth_heading2, third_heading2, all_spaces, \
            punctuations, link, link_number, paren, paren_fr, paren_zh2

logger = loguru.logger
re_category_list = re.compile(r'<link rel="mw:PageProp\/Category" href=".\/(Category:.*?)"')

text_maker = HTML2Text()
text_maker.ignore_links = True
text_maker.ignore_images = True
text_maker.ignore_tables = True
text_maker.ignore_emphasis = False

def get_lang(person_link):
    try:
        json = requests.get("https://en.wikipedia.org/api/rest_v1/page/metadata/"+person_link).json()
    except:
        return [('en', person_link)]
    if "language_links" in json:
        lang_list = json["language_links"]
        return [('en', person_link)]+[(l['lang'], l['titles']['canonical']) for l in lang_list]
    else:
        return [('en', person_link)]

def cut_ref(text, lang_wiki):
    if lang_wiki == "enwiki":
        return cut_references.sub(r"\1",text)
    elif lang_wiki == "eswiki":
        return cut_references_es.sub(r"\1",text)
    elif lang_wiki == "frwiki":
        text = cut_references_fr.sub(r"\1",text)
        return cut_references_fr2.sub(r"\1",text)
    elif lang_wiki == "kowiki":
        return cut_references_ko.sub(r"\1",text)
    elif lang_wiki == "ruwiki":
        return cut_references_ru.sub(r"\1",text)
    else:
        raise ValueError("unsupported lang: "+lang_wiki)

def get_category(person_id, lang_wiki): 
    """_summary_

    Args:
        person_id (str): Wikipedia page ID.

    Returns:
        List[str]: List of categories that the person belongs to.
    """
    if lang_wiki == "enwiki":
        txt = requests.get("https://en.wikipedia.org/api/rest_v1/page/html/"+person_id).text.replace("\n","")
        categories = re_category_list.findall(txt)
        return categories
    else:   
        return [] # NOTE: haven't implemented this for other languages yet.

def get_text(person_link, lang_wiki):
    # txt = requests.get("https://en.wikipedia.org/api/rest_v1/page/html/"+person).text.replace("\n","")
    txt = requests.get(person_link).text.replace("\n","")
    txt = clean_html(txt, lang_wiki)
    return txt

@dataclass
class Paragraph:
    clean_text: str

@dataclass
class Header:
    text: str
    level: int



def clean_paragraph(paragraph_elem: bs4.element.Tag) -> Paragraph:
    # use the html2text library to convert the html to text.
    paragraph = text_maker.handle(str(paragraph_elem))

    paragraph = re.sub(r"\n", " ", paragraph)
    # remove the reference links.
    paragraph = re.sub(r"\[\d+\]", "", paragraph)
    # remove text that is in parentheses.
    paragraph = re.sub(r'\([^)]*\)', "", paragraph) # TODO: this leaves a blank space, which is not ideal.
    # remove text that is in brackets.
    paragraph = re.sub(r'\[[^)]*\]', "", paragraph) # TODO: this might also leave a blank space.

    # remove the markdown formatting for bold and italics.
    paragraph = re.sub(r"\*\*", "", paragraph)
    paragraph = re.sub(r"_", "", paragraph)
    paragraph = paragraph.strip()
    return Paragraph(paragraph)

def retrieve_all_sentences(content_blocks: List[Union[Paragraph, Header]]) -> List[str]:
    all_sentences = []
    for paragraph in filter(lambda x: isinstance(x, Paragraph), content_blocks):
        paragraph_text = paragraph.clean_text
        sentences = sent_tokenize(paragraph_text)
        all_sentences.extend(sentences)
    return all_sentences

def clean_header(header_elem: bs4.element.Tag) -> Header:
    # get the level of the header.
    level = int(header_elem.name[1])
    # get the text of the header.
    header_text = header_elem.text
    return Header(header_text, level)
    
def remove_non_sentences(content_div: bs4.element.Tag, wiki_lang: str) -> bs4.element.Tag:
    hatnotes = content_div.find_all('div', class_='hatnote')
    for hatnote in hatnotes:
        hatnote.decompose()
    
    # remove mw-editsection
    edit_sections = content_div.find_all('span', class_='mw-editsection')
    for edit_section in edit_sections:
        edit_section.decompose()

    # remove <p> that have navbar in their class.
    navbars = content_div.find_all('p', class_='navbar')
    for navbar in navbars:
        navbar.decompose()

    # remove the info box if it exists.
    info_box = content_div.find('table', class_='infobox')
    if info_box:
        info_box.decompose()
    # remove all figures.
    figures = content_div.find_all('figure')
    for figure in figures:
        figure.decompose()
    
    # remove all the mw-empty-elt paragraphs
    empty_paragraphs = content_div.find_all('p', class_='mw-empty-elt')
    for empty_para in empty_paragraphs:
        empty_para.decompose()
    # remove all the tables.
    tables = content_div.find_all('table')
    for table in tables:
        table.decompose()
    # remove all the lists.
    lists = content_div.find_all('ul')
    for list_ in lists:
        list_.decompose()
    # remove all the images.
    images = content_div.find_all('img')
    for image in images:
        image.decompose()
    # remove all the audio files.
    audio_files = content_div.find_all('audio')
    for audio_file in audio_files:
        audio_file.decompose()
    # remove all the video files.
    video_files = content_div.find_all('video')
    for video_file in video_files:
        video_file.decompose()
    # remove all the references.
    references = content_div.find_all('div', class_='reflist')
    for reference in references:
        reference.decompose()

# TODO: fill this in
def _filter_empty_sections(important_content_elems: List[Union[Paragraph, Header]]) -> List[Union[Paragraph, Header]]:
    # filter out headers where they don't enclose any paragraphs.
    filtered_important_content_elems = []


def get_text(page_link, wiki_lang) -> List[Union[Paragraph, Header]]:
    #### step 1: requesting the html
    # get the html through a request.

    # do try/except 3 times.
    for _ in range(3):
        try:
            session = HTMLSession()
            # html = requests.get(page_link, timeout=(3.05, 5)).html.render() # first is connect timeout, second is read timeout.
            response = session.get(page_link)
            response.html.render() # first is connect timeout, second is read timeout.
            html = response.html.raw_html
            break
        except requests.exceptions.Timeout:
            print("timeout error")
            continue

    soup = bs4.BeautifulSoup(html, 'html.parser')
    # keep only the #mw-content-text div.
    content_div = soup.find('div', id='mw-content-text')

    ### Step 2 removing large swathes of the page
    remove_non_sentences(content_div, wiki_lang) # NOTE: warning, this modifies the content_div in place.

    # iterate over the children of the content div. 
    important_content_elems = []
    print("looking for p, h2, h3")
    for element in soup.find_all(lambda tag: tag.name in ['p', 'h2', 'h3']):
        if element.parent.name == 'blockquote':
            logger.info(f"Found a quote: appending to previous paragraph.")
            quote_paragraph = clean_paragraph(element)
            important_content_elems[-1] = Paragraph(important_content_elems[-1].clean_text + ' "' + quote_paragraph.clean_text + '"')
        if element.name == 'p':
            important_content_elems.append(clean_paragraph(element))
        elif element.name == 'h2' or element.name == 'h3':
            important_content_elems.append(clean_header(element))
    # TODO: add call to filter headers for empty sections.
    return important_content_elems

# TODO: there might be an issue here when getting the segmented text.
def get_headings(t):
    def _get_headings(heading_list, heading="## ",second=True):
        if len(heading_list)==1:
            if second:
                return [["summary",heading_list[0]]]
            else:
                return []
        res = []
        _head = None
        for i, h in enumerate(heading_list):
            if i == 0 and not h.startswith("#") and second:
                res.append(["summary",h])
                continue
            if h.startswith(heading):
                _head = h.replace("#","").strip().lower()
            else:
                if _head is None:
                    continue
                if not second:
                    h = fourth_heading2.sub(" ",h)
                    h = all_spaces.sub(" ",h)
                res.append([_head, h])
                _head=None
        return res
    segmented = {}
    seconds = re.split(r"\s(#{2}\s{1}.*?)\s{2}",t)
    segmented["second"]=_get_headings(seconds, "## ", True)
    segmented["third"]= [_get_headings(re.split(r"\s(#{3}\s{1}.*?)\s{2}",h_text), "### ", False) for h, h_text in segmented["second"]]
    for i, (h, h_text) in enumerate(segmented["second"]):
        h_text = fourth_heading2.sub("  ",h_text)
        h_text = third_heading2.sub("  ",h_text)
        h_text = all_spaces.sub(" ",h_text)
        segmented["second"][i][1] = h_text
    return segmented

def _verify_previous_revision_info(revision_info_div: bs4.element.Tag, lang: str):
    if lang == "enwiki":
        assert "old revision" in revision_info_div.find('p').text 
    elif lang == "frwiki":
        assert "version archivée" in revision_info_div.text
    elif lang == "eswiki":
        assert "versión antigua" in revision_info_div.text
    elif lang == "ruwiki":
        assert "старая версия" in revision_info_div.text
    elif lang == "kowiki":
        # assert "이전 버전" in revision_info_div.text, ipdb.set_trace()
        pass
    else:
        raise ValueError(f"Language {lang} not supported.")

def cut_paren(text, lang_wiki):
    if lang_wiki == "enwiki":
        return paren.sub("",text)
    elif lang_wiki == "eswiki":
        return paren.sub("",text)
    elif lang_wiki == "frwiki":
        text = paren.sub("",text)
        return paren_fr.sub(r"\1",text)
    elif lang_wiki == "zh":
        text = paren.sub("",text)
        # text = paren_zh.sub("",text)
        return paren_zh2.sub(r"\1",text)
    elif lang_wiki == "kowiki":
        return paren.sub("",text)
    elif lang_wiki == "ruwiki":
        text = paren.sub("",text)
        return paren_fr.sub(r"\1",text)
    else:
        raise ValueError("unsupported lang: "+lang_wiki)
    
def _verify_current_revision_info(revision_info_div: bs4.element.Tag, lang: str):
    # TODO: ask Chan if we really need these.
    if lang == "enwiki":
        assert "current revision" in revision_info_div.find('p').text
    elif lang == "frwiki":
        assert "version actuelle" in revision_info_div.text
    elif lang == "eswiki":
        assert "versión actual" in revision_info_div.text
    elif lang == "ruwiki":
        assert "текущая версия" in revision_info_div.text
    elif lang == "kowiki":
        # assert "현재 버전" in revision_info_div.text, ipdb.set_trace()
        # NOTE: commented out, maybe it's needed 
        pass

    else:
        raise ValueError(f"Language {lang} not supported.")

def clean_html(text, lang_wiki: str):
    # if lang_wiki != "enwiki":
    #     ipdb.set_trace()
    text_soup = bs4.BeautifulSoup(text, 'html.parser')
    # remove the div with mw-content-subtitle element.
    content_revision_info_previous = text_soup.find('div', id='mw-revision-info')
    content_revision_info_current = text_soup.find('div', id='mw-revision-info-current')
    if content_revision_info_previous: 
        # assert that the content revision info has a <p> tag containing the text "old revision"
        _verify_previous_revision_info(content_revision_info_previous, lang_wiki)
        content_revision_info_previous.decompose()
    if content_revision_info_current:
        # assert "current revision" in content_revision_info_current.find('p').text
        _verify_current_revision_info(content_revision_info_current, lang_wiki)
        content_revision_info_current.decompose()
    text = str(text_soup)
    t = cut_table.sub("  ", text)
    t = cut_list.sub(" ",t)
    t = cut_sup.sub("",t)
    t = cut_note.sub("",t)
    t = text_maker.handle(t).replace("\n"," ")
    t = cut_first_table.sub(r"\2",t)
    t = cut_ref(t, lang_wiki)
    t = cut_references2.sub(r"\1",t)
    t = double_paren.sub("",t)
    t = link.sub(r"\1",t)
    t = link_number.sub("",t)
    t = emphasis.sub(r"\1",t)
    t = cut_paren(t, lang_wiki)
    t = bold.sub(r"\1",t)
    t = t.replace(" > "," ")
    if lang_wiki == "enwiki":
        t = t.replace("\'t", " \'t")
        t = t.replace("\'s", " \'s")
        t = t.replace("\'ve", " \'ve")
        t = t.replace("\'m", " \'m")
        t = t.replace("\'re", " \'re")
    
    segmented = get_headings(t)
    second_headings_separated = second_heading_separation.findall(t)
    second_headings = [h[0] for h in second_headings_separated]
    fourth_headings = fourth_heading.findall(t)
    t = fourth_heading.sub("  ",t)
    third_headings = third_heading.findall(t)
    t = third_heading.sub("  ",t)
    second_headings = second_heading.findall(t)
    t = second_heading.sub("  ",t)
    # t = punctuations.sub(r" \1 ",t)
    t = all_spaces.sub(" ",t)
    return t, (second_headings, third_headings, fourth_headings), segmented

re_he = re.compile("[^a-zA-Z0-9]+he ")
re_she = re.compile("[^a-zA-Z0-9]+she ")
re_his = re.compile("[^a-zA-Z0-9]+his ")
re_her = re.compile("[^a-zA-Z0-9]+her ")
re_him = re.compile("[^a-zA-Z0-9]+him ")

def get_gender_with_text(txt):
    txt = txt.lower()
    freq_he = len(re_he.findall(txt))+len(re_his.findall(txt))+len(re_him.findall(txt))
    freq_she = len(re_she.findall(txt))+len(re_her.findall(txt))
    gender = None
    if freq_she > freq_he:
        gender = "F"
    elif freq_he > freq_she:
        gender = "M"
    return gender

def get_info(wiki_link: str, lang_wiki: str):
    """Gets the information from every section of a Wikipedia page.

    Args:
        wiki_link (str): Link to the person's wikipedia page and the person's name.
        lang_wiki (str): 

    Returns:
        Tuple[str, Dict[str, Any]]: _description_
    """
    wiki_link = wiki_link.replace("/wiki/","")
    # link is of the form 'https://en.wikipedia.org/w/index.php?title=Scottie_Barnes&oldid=910610546'
    # get the title 
    person_id = parse_qs(urlparse(wiki_link).query)['title'][0]

    person_info = {}
    person_info["langs"] = get_lang(wiki_link) # TODO: needs to be replaced.
    person_info["categories"] = get_category(person_id, lang_wiki) # 
    txt, section_names, section_text = get_text(wiki_link, lang_wiki)
    person_info["gender"] = get_gender_with_text(txt) # count of gendered pronouns 
    person_info["text"] = txt # unsplit text
    person_info["section-names"] = section_names # lengths of sections should be the same as section-text.
    person_info["section-text"] = section_text
    return wiki_link, person_info