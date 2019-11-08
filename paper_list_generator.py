#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Do directory traversal in pwd, find all pdf file.
   Search those files' names on google scholar,
   then save reference infos to a csc file, 
   meanwhile save those BibTexs in another file.
"""
import os
import importlib
import requests
import time
import random
import re

from bs4 import BeautifulSoup
import pandas as pd

PWD = os.getcwd()
QUERY_SLEEP_TIME = 1
PAPERLIST_FILE = os.path.join(PWD, 'paper_list_test.csv')
BIBTEX_FILE = os.path.join(PWD, 'bibtexs')
ERRORLIST_FILE = os.path.join(PWD, 'error_list.csv')
# Convert cookies from Chrome inspector in https://repl.it/repls/BisquePrizeMapping
COOKIES = {}
HEADERS = {
    'accept-language': 'en-US,en',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml'
    }
HOST = 'https://scholar.google.com'
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.cookies.update(COOKIES)

def delay():
    time.sleep(1+random.normalvariate(1, 0.3))

class Publication:
    def __init__(self, keyword):
        self.attr = {
            'id': lambda soup: soup.find_all('h3', class_='gs_rt')[0].contents[-1].get('id'),
            'title': lambda soup: soup.find_all('h3', class_='gs_rt')[0].contents[-1].string,
            'year': lambda soup: re.findall(r'19\d\d|20\d\d', soup.find_all('div', class_='gs_a')[0].contents[-1])[-1],
            'url': lambda soup: soup.find_all('h3', class_='gs_rt')[0].contents[-1].get('href'),
            'citedby': lambda soup: re.findall(r'\d+', soup.find_all('div', class_='gs_fl')[1].contents[4].string)[0],
            'eprint': lambda soup: soup.find_all('div', class_='gs_or_ggsm')[0].contents[0].get('href')
        }
        self.bibtex = ''
        html = self._search(keyword)
        self._fill(html)
        self._get_bib()

    def _search(self, keyword):
        query = HOST + '/scholar?hl=en&as_sdt=0%2C5&q=' + keyword.replace(' ', '+')
        delay()
        r = SESSION.get(query)
        if r.status_code == 200:
            return r.text
        else:
            raise Exception("Search failed, status code: %d" % (r.status_code))
            
    def _fill(self, html):
        html = html.replace(u'\xa0', u' ')
        soup = BeautifulSoup(html, 'html.parser')
        tmp = {}
        for k, v in self.attr.items():
            try:
                tmp[k] = v(soup)
            except:
                tmp[k] = 'N/A'
        self.attr = tmp

    def _get_bib(self):
        query = HOST + '/scholar?q=info:' + self.attr['id'] + ':scholar.google.com/&output=cite&scirp=0&hl=en'
        delay()
        r = SESSION.get(query)
        if r.status_code == 200:
            html = r.text.replace(u'\xa0', u' ')
            soup = BeautifulSoup(html, 'html.parser')
            query = soup.find_all('a', class_='gs_citi')[0].get('href')
            delay()
            r = SESSION.get(query)
            if r.status_code == 200:
                html = r.text.replace(u'\xa0', u' ')
                self.bibtex = html

def find_pdf(rootDir):
    pdfs = []
    tot = 0
    for dirName, subdirList, fileList in os.walk(rootDir):
        catagory = os.path.relpath(dirName, rootDir)
        for fname in fileList:
            title, ext = os.path.splitext(fname)
            if ext.lower()== '.pdf':
                tot += 1
                pdfs.append((catagory, title))
                print('Found catagory title: %s %s, total: %d' % (catagory, title, tot))
    return pdfs

""" Search title on google scholar like this:
    search_query = scholarly.search_pubs_custom_url('/scholar?hl=en&as_sdt=0%2C5&q='\
    'A critical review and analysis on techniques of speech recognition- The road ahead')
    # 'hl=en&as_sdt=0%2C5' is crucial to insure English paper being searched
"""
def search_pubs(pdfs):
    paperlist = []
    errorlist = []
    biblist = []
    tot = 0
    for pdf in pdfs:
        catagory = pdf[0]
        title = pdf[1]
        try:
            pub = Publication(title)
            paperlist.append((catagory, 
                    pub.attr['year'],
                    pub.attr['citedby'], 
                    pub.attr['title'], 
                    pub.attr['url'],
                    pub.attr['eprint']))
            
            biblist.append(pub.bibtex)
            tot += 1
            print('Downloaded %s %s, total %d' % (catagory, title, tot))
        except Exception as err:
            errorlist.append((catagory, title))
            print(err)
            print('Skip %s %s' % (catagory, title))
        
    return paperlist, biblist, errorlist

def save_paperlist(paperlist, fname):
    try:
        df = pd.DataFrame(paperlist, columns=['Catagory', 'Year', '# of Cite by', 'Title', 'URL', 'ePrint'])
        df.to_csv(fname, index=False)
    except Exception as err:
        print(err)
        print("Save paper list failed.")

def save_biblist(biblist, fname):
    try:
        with open(fname,'w') as f:
            for bib in biblist:
                f.writelines(bib)
    except Exception as err:
        print(err)
        print('Save BibTex failed.')

def save_errorlist(errorlist, fname):
    try:
        df = pd.DataFrame(errorlist, columns=['Catagory', 'Title'])
        df.to_csv(fname, index=False)
    except Exception as err:
        print(err)
        print("Save error list failed.")

def main():
    pdfs = find_pdf(PWD)
    paperlist, biblist, errorlist = search_pubs(pdfs)
    save_paperlist(paperlist, PAPERLIST_FILE)
    save_biblist(biblist, BIBTEX_FILE)
    save_errorlist(errorlist, ERRORLIST_FILE)

if __name__ == "__main__":
    main()