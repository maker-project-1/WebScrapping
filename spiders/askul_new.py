import os.path as op

from lxml import etree

parser = etree.HTMLParser(encoding='utf-8')
from time import sleep
from urllib.parse import urlsplit, parse_qs
from create_csvs import create_csvs
from ers import all_keywords_jp as keywords, fpath_namer, mh_brands, clean_url, shop_inventory_lw_csv
from matcher import BrandMatcher
from custom_browser import CustomDriver
from parse import parse
from ers import clean_xpathd_text
import re
from ers import COLLECTION_DATE, file_hash, img_path_namer, TEST_PAGES_FOLDER_PATH
from validators import validate_raw_files, check_products_detection



# Init variables and assets
shop_id = "askul"
root_url = "https://lohaco.jp"
country = "JP"
searches, categories, products = {}, {}, {}
driver = CustomDriver(headless=False)
brm = BrandMatcher()

def getprice(pricestr):
    if pricestr == '':
        return pricestr
    pricestr = re.sub("[^0-9]", "", pricestr)
    price = parse('{pound:d}', pricestr)
    if price:
        return price.named['pound'] * 100


###################
# # CTG page xpathing #
###################
exple_ctg_page_path = op.join(TEST_PAGES_FOLDER_PATH, "askul", 'ctg_page_test.html') # TODO : store the file
ctg, test_categories, test_products = '', {'': []}, {}


def ctg_parsing(fpath, ctg, categories, products):  # TODO : modify xpaths
    tree = etree.parse(open(fpath, 'rb'), parser=parser)
    for li in tree.xpath('//ul[@class="lineupItemList"]/li'):
        produrl = li.xpath('.//p[@class="itemName"]/a/@href')[0]
        produrl = parse_qs(urlsplit(produrl).query)['url'][0] if 'url' in parse_qs(urlsplit(produrl).query) else produrl
        products[produrl] = {
            'pdct_name_on_eretailer': clean_xpathd_text(li.xpath('.//p[@class="itemName"]//text()'), unicodedata_normalize=True),
            'raw_price': clean_xpathd_text(li.xpath('.//p[@class="price"]/strong/text()')[:1], unicodedata_normalize=True),
            'raw_promo_price': clean_xpathd_text(li.xpath('.//xpath/text()'), unicodedata_normalize=True),
            'volume': clean_xpathd_text(li.xpath('.//p[@class="itemName"]//text()'), unicodedata_normalize=True),
            'pdct_img_main_url': "".join(li.xpath('.//span[@class="imgBox"]//img/@data-src')[0]),
        }
        products[produrl]['brnd'] = brm.find_brand(products[produrl]['pdct_name_on_eretailer'])['brand']
        print(products[produrl], produrl)
        products[produrl]['price'] = getprice(products[produrl]['raw_price'])
        products[produrl]['promo_price'] = getprice(products[produrl]['raw_promo_price'])
        products[produrl]['pdct_img_main_url'] = clean_url(products[produrl]['pdct_img_main_url'].replace('_L.', '_3L.'), root_url)
        print(products[produrl])

        categories[ctg].append(produrl)
    return categories, products


ctg_parsing(exple_ctg_page_path, ctg, test_categories, test_products)

###################
# # KW page xpathing #
###################

exple_kw_page_path = op.join(TEST_PAGES_FOLDER_PATH, "askul", 'kw_page_test.html') # TODO : store the file
kw, test_searches, test_products = '', {'': []}, {}


def kw_parsing(fpath, kw, searches, products):  # TODO : modify xpaths
    tree = etree.parse(open(fpath, 'rb'), parser=parser)
    for li in tree.xpath('//ul[@class="lineupItemList"]/li'):
        produrl = li.xpath('.//a/@href')[0]
        produrl = parse_qs(urlsplit(produrl).query)['url'][0] if 'url' in parse_qs(urlsplit(produrl).query) else produrl
        products[produrl] = {
            'pdct_name_on_eretailer': clean_xpathd_text(li.xpath('.//p[@class="itemName"]//text()'), unicodedata_normalize=True),
            'raw_price': clean_xpathd_text(li.xpath('.//p[@class="price"]/strong/text()')[:1], unicodedata_normalize=True),
            'raw_promo_price': clean_xpathd_text(li.xpath('.//xpath/text()'), unicodedata_normalize=True),
            'volume': clean_xpathd_text(li.xpath('.//p[@class="itemName"]//text()'), unicodedata_normalize=True),
            'pdct_img_main_url': "".join(li.xpath('.//span[@class="imgBox"]//img/@src')[0]),
        }
        products[produrl]['brnd'] = brm.find_brand(products[produrl]['pdct_name_on_eretailer'])['brand']
        print(products[produrl], produrl)
        products[produrl]['price'] = getprice(products[produrl]['raw_price'])
        products[produrl]['promo_price'] = getprice(products[produrl]['raw_promo_price'])
        products[produrl]['pdct_img_main_url'] = clean_url(products[produrl]['pdct_img_main_url'].replace('_L.', '_3L.'), root_url)
        print(products[produrl])

        searches[kw].append(produrl)
    return searches, products


kw_parsing(exple_kw_page_path, kw, test_searches, test_products)


###################
# # PDCT page xpathing #
###################
exple_pdct_page_path = op.join(TEST_PAGES_FOLDER_PATH, shop_id, 'pdct_page_test.html') # TODO: store the file
# exple_pdct_page_path = "/code/mhers/cache/w_9/isetan/pdct/＜クリュッグ＞ロゼ ハーフサイズ-page0.html"
test_url, test_products = '', {'': {}}


def pdct_parsing(fpath, url, products): # TODO : modify xpaths
    tree = etree.parse(open(fpath), parser=parser)
    products[url].update({
        # 'volume': clean_xpathd_text(tree.xpath('.//*[@class="item-info"]//tr//td//text()')[:3], unicodedata_normalize=True),
        'pdct_img_main_url': clean_url(''.join(tree.xpath('//div[@class="images clr"]/img/@src')[:1]), root_url),
        'ctg_denom_txt': ' '.join(tree.xpath('//span[@class="breadcrumb-trail"]//text()')),
    })
    return products

pdct_parsing(exple_pdct_page_path, test_url, test_products)


###################
# # CTG scrapping #
###################

# TODO : complete the urls
urls_ctgs_dict = {
    'champagne': 'https://lohaco.jp/g4/71-5107-5107004-51070040001/?resultCount=100&page={page}',
    'sparkling': 'https://lohaco.jp/g4/71-5107-5107004-51100020005/?resultCount=100&page={page}',
    'still_wines': 'https://lohaco.jp/g2/71-5107/?resultCount=100&page={page}',
    'whisky': 'https://lohaco.jp/g3/71-5111-5110008/?resultCount=100&page={page}',
    'cognac': 'https://lohaco.jp/g4/71-5111-5110009-51100090001/?resultCount=100&page={page}',
    'vodka': 'https://lohaco.jp/g3/71-5111-5110011/?resultCount=100&page={page}',
    'gin': 'https://lohaco.jp/g3/71-5111-5110010/?resultCount=100&page={page}',
    'tequila': 'https://lohaco.jp/g3/71-5111-5110013/?resultCount=100&page={page}',
    'liquor': 'https://lohaco.jp/g3/71-5111-5110007/?resultCount=100&page={page}',
    'white_wine': 'https://lohaco.jp/g3/71-5107-5110002/?resultCount=100&page={page}',
    'red_wine': 'https://lohaco.jp/g3/71-5107-5107002/?resultCount=100&page={page}',
    # 'bourbon': '',#na
    'brandy': 'https://lohaco.jp/g3/71-5111-5110009/?resultCount=100&page={page}',
    'rum': 'https://lohaco.jp/g3/71-5111-5110012/?resultCount=100&page={page}',
}


# Category Scraping - with selenium - multiple pages per category (click on next page)
for ctg, url in urls_ctgs_dict.items():
    categories[ctg] = []
    number_of_pdcts_in_ctg = 0

    for p in range(100):
        fpath = fpath_namer(shop_id, 'ctg', ctg, p)

        if not op.exists(fpath):
            driver.get(url.format(page=p+1))
            sleep(2)
            driver.save_page(fpath, scroll_to_bottom=True)
        categories, products = ctg_parsing(fpath, ctg, categories, products)

        if len(set(categories[ctg])) == number_of_pdcts_in_ctg:
            break
        else:
            number_of_pdcts_in_ctg = len(set(categories[ctg]))
    print(ctg, url, p, len(categories[ctg]))


######################################
# # KW searches scrapping ############
######################################

# KW searches Scraping - with requests - one page per search
kw_search_url = "https://lohaco.jp/ksearch/?searchWord={kw}&resultCount=100"  # TODO : modify URL
for kw in keywords:
    searches[kw] = []
    number_of_pdcts_in_kw_search = 0
    if not op.exists(fpath_namer(shop_id, 'search', kw, 0)):
        print(kw_search_url.format(kw=kw))
        driver.get(kw_search_url.format(kw=kw))

    for p in range(1):
        fpath = fpath_namer(shop_id, 'search', kw, p)
        if not op.exists(fpath):
            sleep(2)
            driver.save_page(fpath, scroll_to_bottom=True)

        searches, products = kw_parsing(fpath, kw, searches, products)

    print(kw, len(searches[kw]))


######################################
# # Product pages scraping ###########
######################################

# Download the pages - with selenium
for url in sorted(list(set(products))):
    d = products[url]
    if d['brnd'] in mh_brands:
        print(d['pdct_name_on_eretailer'], d['volume'])
        url_mod = clean_url(url, root_url=root_url)

        fpath = fpath_namer(shop_id, 'pdct', d['pdct_name_on_eretailer'], 0)
        if not op.exists(fpath):
            driver.get(url_mod)
            sleep(2)
            driver.save_page(fpath, scroll_to_bottom=True)
        products = pdct_parsing(fpath, url, products)
        print(products[url])


######################################
# # Download images        ###########
######################################
# Download images
from ers import download_img

for url, pdt in products.items():
    if 'pdct_img_main_url' in pdt and pdt['pdct_img_main_url'] and brm.find_brand(pdt['pdct_name_on_eretailer'])['brand'] in mh_brands:
        print(pdt['pdct_name_on_eretailer'] + "." + pdt['pdct_img_main_url'].split('.')[-1])
        orig_img_path = img_path_namer(shop_id, pdt['pdct_name_on_eretailer'])
        img_path = download_img(pdt['pdct_img_main_url'], orig_img_path, shop_id=shop_id, decode_content=False, gzipped=False, debug=False)
        if img_path:
            products[url].update({'img_path': img_path, 'img_hash': file_hash(img_path)})

create_csvs(products, categories, searches, shop_id, fpath_namer(shop_id, 'raw_csv'), COLLECTION_DATE)
validate_raw_files(fpath_namer(shop_id, 'raw_csv'))
check_products_detection(shop_id, fpath_namer(shop_id, 'raw_csv'), shop_inventory_lw_csv)
driver.quit()
