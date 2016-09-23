#!/usr/bin/env python3

# Copyright (c) 2016 Ryan Gonzalez
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from bs4.element import Tag, NavigableString
from bs4 import BeautifulSoup
import requests

from functools import reduce, partial
from collections import OrderedDict
import sys

HTML_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
}

URL = 'https://www.reddit.com/r/Xenoblade_Chronicles/comments/5448ll/probe_locations_guide_10_183188_probes_listed/'

VALID_FORMATS = ['markdown']

PROBE_INFO = ['Level', 'Type', 'Segment', 'Location', 'Info']

last_elem = partial(reduce, lambda _, x: x)
just_tags = partial(filter, lambda x: isinstance(x, Tag))

linkify_probe = lambda s: s.replace(' ', '_')

class Document:
    def __init__(self, intro, groups, notes, history, ack):
        self.intro = intro
        self.groups = groups
        self.notes = notes
        self.history = history
        self.ack = ack

    def render_markdown(self):
        res = []

        res.append('#Contents')
        res.append('- [Introduction](#intro)')
        res.append('- [Probe list](#probes-l)')
        for name in self.groups.keys():
            res.append('  - [%s](#%s-l)' % (name, linkify_probe(name)))
        res.append('- [Probe table](#probes-t)')
        for name in self.groups.keys():
            res.append('  - [%s](#%s-t)' % (name, linkify_probe(name)))
        res.append('- [Notes](#notes)')
        res.append('- [Version History](#history)')
        res.append('- [Acknowledgements](#ack)')
        res.append('')

        res.append('#Introduction <a name="intro"></a>')
        res.append('This was automatically scraped from [this url](%s).' % URL)
        res.append('If you have a suggestion to make about the body of this,')
        res.append('please post it to a comment there.')
        res.append('All credit for this goes to NuanceContextEmpathy.')
        res.append('')
        res.append('##Original introduction')
        res.append('\n\n'.join(self.intro))
        res.append('')

        res.append('#Probe list <a name="probes-l"></a>')
        for name, probes in self.groups.items():
            res.append('##%s <a name="%s-l"></a>' % (name, linkify_probe(name)))
            for probe, items in probes.items():
                res.append('###' + probe)
                if len(items) == 1 and isinstance(items[0], str):
                    res.append(items[0])
                else:
                    for item in items:
                        res.append('- **%s**: %s' % item)
                res.append('')

        res.append('#Probe table <a name="probes-t"></a>')
        for name, probes in self.groups.items():
            res.append('##%s <a name="%s-t"></a>' % (name, linkify_probe(name)))
            res.append('| Probe | %s |' % ' | '.join(PROBE_INFO))
            res.append('| --- |'*(len(PROBE_INFO)+1))
            for probe, items in probes.items():
                cols = [probe]
                if len(items) == 1 and isinstance(items[0], str):
                    cols.extend(['None']*len(PROBE_INFO))
                    cols.append(items[0])
                else:
                    items_d = dict(items)
                    cols.extend([items_d[k] for k in PROBE_INFO[:-1]])
                    cols.append('None')
                res.append('| %s |' % ' | '.join(cols))
            res.append('')

        info = [
            ('Notes', 'notes'),
            ('Version History', 'history'),
            ('Acknowledgements', 'ack'),
        ]
        for ititle, ilist in info:
            res.append('#%s <a name="%s"></a>' % (ititle, ilist))
            for item in getattr(self, ilist):
                res.append('- ' + item)
            res.append('')

        return res


def get_page():
    return BeautifulSoup(requests.get(URL, headers=HTML_HEADERS).content, 'lxml')

def element_contents_str(elem):
    return elem.encode_contents().decode('utf-8')

def parse_page(page):
    start = page.find('h2', text='Introduction')
    groups = OrderedDict()
    is_end = False
    intro = []
    notes = None
    history = None
    ack = None
    for sibling in just_tags(start.next_siblings):
        if groups:
            last_group = last_elem(groups.values())
        if sibling.name == 'h2':
            if sibling.string == 'Notes':
                is_end = True
                notes = []
            elif sibling.string == 'Version History':
                history = []
            elif sibling.string == 'Acknowledgements':
                ack = []
            else:
                groups[sibling.string] = OrderedDict()
        elif sibling.name == 'h1' and sibling.string.startswith('Probe'):
            last_group[sibling.string] = []
        elif not is_end and groups and last_group:
            last_probe = last_elem(last_group.values())
            if sibling.name == 'ul':
                for li in just_tags(sibling.contents):
                    last_probe.append((li.contents[0].string,
                                       li.contents[1][2:]))
            elif sibling.name == 'p':
                last_probe.append(element_contents_str(sibling))
        elif is_end:
            for target in ack, history, notes:
                if target is not None:
                    break
            for li in just_tags(sibling.contents):
                target.append(element_contents_str(li))
        elif not groups:
            intro.append(element_contents_str(sibling))

    return Document(intro, groups, notes, history, ack)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in VALID_FORMATS:
        sys.exit('usage: %s <format: one of %s> <output file>' %
                 (sys.argv[0], ', '.join(VALID_FORMATS)))
    _, format, output = sys.argv
    format = sys.argv[1]
    print('Retrieving page...')
    page = get_page()
    print('Parsing page...')
    doc = parse_page(get_page())
    print('Rendering page...')
    rendered = '\n'.join(getattr(doc, 'render_' + format)())
    print('Writing output file %s...' % output)
    with open(output, 'w') as f:
        f.write(rendered)
    print('Done!')


if __name__ == '__main__':
    main()
