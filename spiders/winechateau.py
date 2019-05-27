
import os.path as op
import re
from io import BytesIO

from lxml import etree

parser = etree.HTMLParser(encoding='utf-8')
from time import sleep
from urllib.parse import urlsplit, parse_qs
import requests
import requests_cache, imghdr
from validators import validate_raw_files
from create_csvs import create_csvs
from ers import all_keywords_usa as keywords, fpath_namer, mh_brands, clean_url, headers

from matcher import BrandMatcher
from ers import COLLECTION_DATE, file_hash, img_path_namer
import shutil
from custom_browser import CustomDriver
from parse import parse


# Init variables and assets
shop_id = "winechateau"
root_url = "http://www.winechateau.com" 
requests_cache.install_cache(fpath_namer(shop_id, 'requests_cache'))
country = "USA"


searches, categories, products = {}, {}, {}
# If necessary
driver = CustomDriver(headless=True)


def getprice(pricestr):
    pricestr = re.sub("[^0-9.$]", "", pricestr)
    if pricestr == '':
        return pricestr
    price = parse('${pound:d}.{pence:d}', pricestr)
    if price is None:
        price = parse('{pence:d}p', pricestr)
        return price.named['pence']
    else:
        return price.named['pound'] * 100 + price.named['pence']


urls_ctgs_dict = {
    "vodka": "https://www.winechateau.com/collections/vodka#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "sparkling": "https://www.winechateau.com/collections/champagne-sparkling#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "cognac": "https://www.winechateau.com/collections/cognacs#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "champagne": "https://www.winechateau.com/collections/vodka#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "still_wines": "https://www.winechateau.com/collections/white-wine#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "whisky": "https://www.winechateau.com/collections/whiskeys#/?res_per_page=90&Collections=Whiskeys&search_return=all&page={page}",
    "red_wine": "https://www.winechateau.com/collections/red-wine#/?res_per_page=90&search_return=all&page={page}",
    "white_wine": "https://www.winechateau.com/collections/white-wine#/?res_per_page=90&search_return=all&page={page}",
    "gin": "https://www.winechateau.com/collections/spirits?page=1&rb_snize_facet6=Gins&res_per_page=90&search_return=all&page={page}",
    "tequila": "https://www.winechateau.com/collections/spirits?page=1&rb_snize_facet6=Tequila&res_per_page=90&search_return=all&page={page}",
    "liquor": "https://www.winechateau.com/collections/spirits?page=1&rb_snize_facet6=Cordials%20%26%20Liquers&res_per_page=90&search_return=all&page={page}",
    "brandy": "https://www.winechateau.com/collections/spirits?page=1&rb_snize_facet6=Brandies&res_per_page=90&search_return=all&page={page}",
}

# Category Scraping
for ctg, url in urls_ctgs_dict.items():
    categories[ctg] = []
    number_of_pdcts_in_ctg = 0
    for p in range(100):
        urlp = url.format(page=p+1)
        
        fpath = fpath_namer(shop_id, 'ctg', ctg, p)
        if not op.exists(fpath):
            driver.get(urlp)
            sleep(2)
            driver.save_page(fpath)
        tree = etree.parse(BytesIO(open(fpath, 'rb').read()), parser=parser)

        for li in tree.xpath('//li[@class="snize-product"]'):
            # produrl = li.xpath('.//div[@class="box-grid-main"]/a/@href')[0]
            produrl = li.xpath('./a/@href')[0]
            produrl = parse_qs(urlsplit(produrl).query)['url'][0] if 'url' in parse_qs(urlsplit(produrl).query) else produrl
            produrl = clean_url(produrl, root_url)
            products[produrl] = {
                # 'pdct_name_on_eretailer': ' '.join(''.join(li.xpath('.//div[contains(@class, "item__title")]/a/text()')).split()),
                'pdct_name_on_eretailer': ' '.join(''.join(li.xpath('.//span[@class="snize-title"]//text()')).split()),
                # 'raw_price': ' '.join(''.join(li.xpath('.//div[@class= "grid-view-item__meta clearfix price_wrap"]/s//text()')[:1]).split()),
                'raw_price': ' '.join(''.join(li.xpath('.//span[@class="snize-discounted-price"]//text()')).split()),
                # 'raw_promo_price': ' '.join(''.join(li.xpath('.//div[@class= "grid-view-item__meta clearfix price_wrap"]/span[last()]//text()')).split()),
                'raw_promo_price': ' '.join(''.join(li.xpath('.//span[@class="snize-price"]//text()')).split()),
            }
            print('products:',products[produrl], produrl)
            products[produrl]['price'] = getprice(products[produrl]['raw_price'])
            products[produrl]['promo_price'] = getprice(products[produrl]['raw_promo_price'])
            print(products[produrl])
            
            categories[ctg].append(produrl)

        # Checking if it was the last page
        if len(set(categories[ctg])) == number_of_pdcts_in_ctg:
            break
        else:
            number_of_pdcts_in_ctg = len(set(categories[ctg]))
        # if not r.from_cache:
        #     sleep(2)
print([(c, len(categories[c])) for c in categories])




# KW searches Scraping - with selenium - with nb page hard-coded in url - multiple page per search
search_url = "https://www.winechateau.com/pages/search-results-page?q=champagne&page={page}"
for kw in keywords:
    searches[kw] = []
    number_of_pdcts_in_kw_search = 0
    
    for p in range(5):
        # Storing and extracting infos
        urlp = search_url.format(kw=kw,page=p)
        
        fpath = fpath_namer(shop_id, 'search', kw, p)
        if not op.exists(fpath):
            driver.get(urlp)
            sleep(2)
            driver.save_page(fpath)
        tree = etree.parse(BytesIO(open(fpath, 'rb').read()), parser=parser)
        
        # r = requests.get(urlp)
        # with open('/tmp/' + shop_id + '_' + kw + '.html', 'wb') as f:
        #     f.write(r.content)
        # tree = etree.parse(BytesIO(r.content), parser=parser)

        # for li in tree.xpath('//div[@id="Collection"]/div/div[contains(@class, "grid__item")]'):
        for li in tree.xpath('//li[@class="snize-product"]'):
            # produrl = li.xpath('.//div[@class="box-grid-main"]/a/@href')[0]
            produrl = li.xpath('./a/@href')[0]
            produrl = parse_qs(urlsplit(produrl).query)['url'][0] if 'url' in parse_qs(
                urlsplit(produrl).query) else produrl
            produrl = clean_url(produrl, root_url)
            products[produrl] = {
                'pdct_name_on_eretailer': ' '.join(
                    # ''.join(li.xpath('.//div[contains(@class, "item__title")]/a/text()')).split()),
                    ''.join(li.xpath('.//span[@class="snize-title"]//text()')).split()),
                'raw_price': ' '.join(''.join(
                    li.xpath('.//span[@class="snize-discounted-price"]//text()')[:1]).split()),
                'raw_promo_price': ' '.join(''.join(li.xpath(
                    './/span[@class="snize-price"]//text()')).split()),
            }
            print(products[produrl], produrl)
            products[produrl]['price'] = getprice(products[produrl]['raw_price'])
            products[produrl]['promo_price'] = getprice(products[produrl]['raw_promo_price'])
            print(products[produrl])

            searches[kw].append(produrl)
        if len(set(searches[kw])) == number_of_pdcts_in_kw_search:
            break
        else:
            number_of_pdcts_in_kw_search = len(set(searches[kw]))
        # if not r.from_cache:
        #     sleep(2)
    print(kw, p, len(searches[kw]))




# Download the pages - with selenium
brm = BrandMatcher()
for url in sorted(list(set(products))):
    d = products[url]
    if brm.find_brand(d['pdct_name_on_eretailer'])['brand'] in mh_brands:
        print(d['pdct_name_on_eretailer'])
        url_mod = clean_url(url, root_url=root_url)
        
        fname = fpath_namer(shop_id, 'pdct', d['pdct_name_on_eretailer'], 0)
        if not op.exists(fname):
            driver.get(url_mod)
            sleep(2)
            driver.save_page(fname, scroll_to_bottom=True)
        tree = etree.parse(open(fname), parser=parser)
        
        # r = requests.get(url_mod, headers)
        # with open('/tmp/' + d['pdct_name_on_eretailer'].replace('/', "-") + '.html', 'wb') as f:
        #     f.write(r.content)
        # tree = etree.parse(BytesIO(r.content), parser=parser)
        
        products[url].update({
            'volume': ' '.join(''.join(tree.xpath('//ul/li/label[@for]//text()')).split()),
            'pdct_img_main_url': clean_url(''.join(tree.xpath('//img[@id="FeaturedImage-product-template"]/@src')), root_url),
            'ctg_denom_txt': ' '.join(' '.join(tree.xpath('//div/nav[@class="bread-crumb"]//text()')).split()),
        })
        print(products[url])
        # if not r.from_cache:
        #     sleep(2)

# Download images
for url, pdt in products.items():
     if 'pdct_img_main_url' in pdt and pdt['pdct_img_main_url'] and brm.find_brand(pdt['pdct_name_on_eretailer'])['brand'] in mh_brands:
         print(pdt['pdct_name_on_eretailer'] + "." + pdt['pdct_img_main_url'].split('.')[-1])
         print(pdt['pdct_img_main_url'])
         response = requests.get(pdt['pdct_img_main_url'], stream=True, verify=False, headers=headers)
         # response.raw.decode_content = True
         tmp_file_path = '/tmp/' + shop_id + 'mhers_tmp_{}.imgtype'.format(abs(hash(pdt['pdct_img_main_url'])))
         img_path = img_path_namer(shop_id, pdt['pdct_name_on_eretailer'])
         with open(tmp_file_path, 'wb') as out_file:
             shutil.copyfileobj(response.raw, out_file)
         if imghdr.what(tmp_file_path) is not None:
             img_path = img_path.split('.')[0] + '.' + imghdr.what('/tmp/' + shop_id + 'mhers_tmp_{}.imgtype'.format(abs(hash(pdt['pdct_img_main_url']))))
             shutil.copyfile('/tmp/' + shop_id + 'mhers_tmp_{}.imgtype'.format(abs(hash(pdt['pdct_img_main_url']))), img_path)
             products[url].update({'img_path': img_path, 'img_hash': file_hash(img_path)})
         else:
             print('Warning :', tmp_file_path, imghdr.what(tmp_file_path))


create_csvs(products, categories, searches, shop_id, fpath_namer(shop_id, 'raw_csv'), COLLECTION_DATE)
validate_raw_files(fpath_namer(shop_id, 'raw_csv'))
driver.quit()
