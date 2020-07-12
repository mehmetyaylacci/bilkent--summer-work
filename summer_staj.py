# -*- coding: utf-8 -*-
import scrapy
from scrapy.crawler import Crawler, CrawlerProcess
import csv
from bs4 import BeautifulSoup as bs
from urllib import request
import time
import logging
from pprint import pprint
import argparse

"""
Author: Mehmet Yaylacı
Year: 2019
Contributors: 
- Alp Sayin (alpsayin.com)
"""

"""
    *As recommended this project will only create two csv files on .txt format
    *Other libraries could also be used, but I've chosen to use scrapy on this project,
please don't recommend me to use other libs (like urllib.requests, selenium or others).
Scrapy is the coolest way to scrape these kinds of data :)
    *I didn't want to create a scrapy project so we will use
a primitive way of using spiders.
    *Try not to crush Bilkent's servers. Adding waiting time for our spiders will
hopefully solve this issue.
    *The information is fetched from: http://mfstaj.cs.bilkent.edu.tr
"""

########

# some global variables to create two csv files on .txt format
first_outfile = "data/first.csv"
second_outfile = "data/second.csv"
second_infile = first_outfile

CUSTOM_SETTINGS = { 'DOWNLOAD_DELAY': 0.1,
                    # 'ITEM_PIPELINES': {'freedom.pipelines.IndexPipeline': 300 }
                    }

"""
    First of the spiders. Just goes through the first sets of pages and extracts links 
with some other information.
"""

class FirstSpider(scrapy.Spider):
    name = 'FirstSpider'
    custom_settings = CUSTOM_SETTINGS
    def __init__(self, *args, **kwargs):
        super(FirstSpider, self).__init__(*args, **kwargs)
        self.companies = dict()


    def start_requests(self):
        # setting custom settings, this will hopefully solve a possible ddos.


        global first_outfile

        csvfile = open(first_outfile, 'w', newline='', encoding="utf-8") # could be 'a' if append
        self.writer = csv.writer(csvfile)

        # these are the headers of csv
        self.writer.writerow(["company", "id", "city", "dep", "sec"])

        allowed_domains = ['mfstaj.cs.bilkent.edu.tr']
        # url = "http://mfstaj.cs.bilkent.edu.tr/visitor/?filter=AllCompanies&page=company"

        with request.urlopen('http://mfstaj.cs.bilkent.edu.tr/visitor/?page=company&start=0') as response:
            html = response.read()
            page = bs(html)
            # page.prettify()
            company_table = page.find('table', {'id':'companies'})
            first_col = company_table.find('td', {'style':'font-size:0.9em;'})
            page_indicator = first_col.find("span", {"style": "font-size:1.2em;"}).getText()
            last_page_num = int(page_indicator.split('/')[1].replace(' ',''))
            logging.debug('last_page_num={}'.format(last_page_num))

        for page_num in range(last_page_num):
            url = "http://mfstaj.cs.bilkent.edu.tr/visitor/?page=company&start={}&filter=AllCompanies".format(page_num)
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        soup = bs(response.text, 'html.parser')
        soup.prettify()

        stuff = []

        all_rows = soup.find_all("tr", class_="company")
        size = len(all_rows)

        former_id = 0  # this checks duplicates. thanks bilkent for the mistakes :(

        for row in all_rows:
            company_info = row.find_all("td")
            name = company_info[0].getText().strip(' ')
            city = company_info[1].getText().strip(' ')
            depts = company_info[2].getText().strip(' ')
            sector = company_info[3].getText().strip(' ')
            cid = company_info[0].find("a")["href"].split('CompanyID=')[1]

            # this is all preparation to eventually move to pandas as that's the industry standard
            new_company = {'name':name, 'city':city, 'depts':depts, 'sector':sector}
            if cid in self.companies:
                self.companies[cid].update(new_company) # this will merge info if there are duplicates while enforcing there are no dupes
            else:
                self.companies[cid] = new_company
                self.writer.writerow([ name,  cid, city, depts, sector])

########

"""
    Second spider. This time we will click on the links and get the company 
pages one by one. Pls don't ddos Bilkent. Bilkent's internet seems it can crush
anytime so pls don't pressure the servers :(
"""

class SecondSpider(scrapy.Spider):
    name = 'SecondSpider'
    custom_settings = CUSTOM_SETTINGS

    def start_requests(self):
        # setting custom settings, this will hopefully solve a possible ddos.

        global second_infile, second_outfile

        csvfile = open(second_infile, 'r', newline='', encoding="utf-8")
        reader = csv.DictReader(csvfile)
        id = []
        allowed_domains = ['mfstaj.cs.bilkent.edu.tr']

        csvfile = open(second_outfile, 'w', newline='', encoding="utf-8")
        self.writer = csv.writer(csvfile)
        self.writer.writerow(["address", "info", "sector", "name", "country", "city", "phone",
                                "fax", "site"])

        for line in reader:
            id.append(line["id"])

        for x in id:
            url = "http://mfstaj.cs.bilkent.edu.tr/visitor/?page=company&content=detail&CompanyID=" + str(x)
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        soup = bs(response.text, 'html.parser')
        stuff = []
        for x in soup.find_all("textarea", class_="inputText"):
            stuff.append(x.getText().strip())

        for x in soup.find_all("input", class_="inputText"):
            stuff.append(x["value"].strip())

        self.writer.writerow(stuff)

########

"""
    Scrapy doesn't let me run two processes subsequently,
so call them one at a time.
"""

def setup_logger():
    FORMAT = '%(asctime)-15s %(name)s - %(levelname)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    logging.debug('DEBUG messages are printed')
    logging.info('INFO messages are printed')
    logging.warning('WARNING messages are printed')
    logging.error('ERROR messages are printed')
    logging.critical('CRITICAL messages are printed')


def main():
    setup_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('crawl_type', help='"list" or "details". Note that you must have run list beforehand to be able to run details')
    args = parser.parse_args()

    if args.crawl_type == 'list':
        spider_instance = Crawler(FirstSpider)
    elif args.crawl_type == 'details':
        spider_instance =  Crawler(SecondSpider)
    else:
        print('Argument must be "list" or "details"')
        return

    process = CrawlerProcess()
    process.crawl(spider_instance)
    logging.info('starting crawling process')
    process.start(stop_after_crawl=True)
    logging.info('crawling process finished')
    process.join()
    logging.info('all crawlers finished')

    if args.crawl_type == 'list':
        print('final companies list')
        pprint(spider_instance.spider.companies)

if __name__ == '__main__':
    main()
