#!/usr/bin/env python

# Script for extracting citation information from PubMed Central (PMC)
# articles in the .nxml XML format.

from __future__ import with_statement

import sys
import re
from functools import partial

from lxml import etree as ET

OUTPUT_ENCODING="UTF-8"

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Extract strings from UniProt XML data.")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("file", metavar="FILE", nargs="+", help="Input UniProt XML file(s).")

    return ap

def _txt(s):
    return s if s is not None else ""

def element_text(e):
    return _txt(e.text) + subelement_text(e)

def subelement_text(e):
    return ''.join([element_text(s)+_txt(s.tail) for s in e])

def respace(s):
    return re.sub(r'\s+', ' ', s.strip())

def extract_text(e):
    return respace(element_text(e))

def extract_surnames(e):
    return ' '.join([extract_text(s) for s in e.xpath('surname')])

def extract_given_names(e):
    return ' '.join([extract_text(s) for s in e.xpath('given-names')])

def extract_given_names_short(e):
    return ''.join([n[0] for n in extract_given_names(e).split(' ')])

def extract_names(e):
    return extract_given_names(e) + ' ' + extract_surnames(e)

def extract_names_short(e):    
    return extract_surnames(e) + ' ' + extract_given_names_short(e)

def format_default(a):
    return ' '.join(a)

def format_wrap(pre, post, a):
    return pre+format_default(a)+post

def format_names(a):
    if len(a) < 1:
        return ''
    elif len(a) < 2:
        return a[0]
    else:
        return ', '.join(a[:-1]) + ' and ' + a[-1]

# note: '[1]' in xpath restricts to first match.
toextract = [
    ('author',  'article-meta/contrib-group/contrib[@contrib-type="author"]/name'),
    ('year',    'article-meta/pub-date[@pub-type="collection"][1]/year[1]'),
    ('title',   'article-meta/title-group[1]/article-title[1]'),
    ('journal', 'journal-meta/journal-id[@journal-id-type="nlm-ta"][1]'),
    ('volume',  'article-meta/volume[1]'),
    ('issue',   'article-meta/issue[1]'),
    ('doi',     'article-meta/article-id[@pub-id-type="doi"][1]'),
    ('pmcid',   'article-meta/article-id[@pub-id-type="pmc"][1]'),
]

extractor = {
    'author'  : extract_names,
    #'author'  : extract_names_short,
    'DEFAULT' : extract_text,
}

formatter = {
    'author' : format_names,
    'year'   : partial(format_wrap, '(', ')'),
    'issue'  : partial(format_wrap, '(', ')'),
    'doi'    : partial(format_wrap, 'doi:', ''),
    'pmcid'  : partial(format_wrap, '(PMCID: PMC', ')'),
    'DEFAULT': format_default,
}

separator = {
    'title'   : '. ', 
    'volume'  : '',
    'DEFAULT' : ' ',
}

def process_front(front, fn):
    all_texts = []
    for label, exp in toextract:
        texts = []
        for e in front.xpath(exp):
            text = extractor.get(label, extractor['DEFAULT'])(e)
            texts.append(text.encode(OUTPUT_ENCODING))
        all_texts.append(formatter.get(label, formatter['DEFAULT'])(texts))
        all_texts.append(separator.get(label, separator['DEFAULT']))
    print ''.join(all_texts)

def process(fn):
    global options

    front_found = False

    for event, element in ET.iterparse(fn, events=("end", )):
        # we're only interested in tracking <front> end events
        if element.tag != "front":
            continue        
        front_found = True

        process_front(element, fn)

        # assume only one <front> per article, skip rest
        break

    if not front_found:
        print >> sys.stderr, "Error: no <front> found in", fn
    
def main(argv):
    global options
    options = argparser().parse_args(argv[1:])

    for fn in options.file:
        process(fn)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
