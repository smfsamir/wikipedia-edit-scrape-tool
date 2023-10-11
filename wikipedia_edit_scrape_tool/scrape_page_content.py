from urllib.parse import urlparse, parse_qs
import bs4
import requests
import re
from html2text import HTML2Text
import os
from .wiki_regexes import cut_list, cut_sup, cut_note, cut_table, cut_first_table,\
    cut_references2, cut_references, cut_references_es, cut_references_fr, cut_references_fr2, cut_references_ko, cut_references_ru,\
          double_paren, emphasis, bold, second_heading, third_heading, fourth_heading, second_heading_separation, fourth_heading2, third_heading2, all_spaces, \
            punctuations, link, link_number, paren, paren_fr, paren_zh2

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