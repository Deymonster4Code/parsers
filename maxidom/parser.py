import time

import requests
from lxml import etree


class MaxiDomParser:
    """
       Парсер товаров площадки maxidom: maxidom.ru

    """

    origin = 'maxidom.ru'
    HEADERS = {'authority': ''}

    # хук каталога
    catalog_hook = "https://www.maxidom.ru/catalog/"
    site_url = "https://www.maxidom.ru"

    def get_sub_categories(self, catalog_hook):
        """
        Рекурсивная функция для получения подкатегорий
        :param catalog_hook: ссылка на родительскую категорию

        """
        result = {
            'name': "Maxidom",
            'url': catalog_hook,
            'children': [],
            'is_stable': True,
        }

        response = requests.get(catalog_hook)
        if response.status_code in [404]:
            result['is_stable'] = True
            return result
        elif response.status_code in [502, 403]:
            result['is_stable'] = False
            return result
        html = etree.HTML(response.text)
        categories_list = []
        for category in html.xpath('//div[@class="it_categories_a"]'):
            category_url = category.xpath('figure/a[2]/@href')[0]
            category_name = category.xpath('figure/a[2]/figcaption/span')[0].text
            if all((category_url, category_name)):
                categories_list.append({
                    "name": category_name,
                    "url": 'https://www.maxidom.ru' + category_url,
                    "children": None,
                })
        if html.xpath('//a[@class="it_categories_a"]'):
            category_url = html.xpath('//a[@class="it_categories_a"]/@href')[0]
            category_name = html.xpath('//a[@class="it_categories_a"]/figure/div/img/@alt')[0]
            if all((category_url, category_name)):
                categories_list.append({
                    "name": str(category_name),
                    "url": 'https://www.maxidom.ru' + str(category_url),
                    "children": None,
                })
        result['children'] = categories_list
        return result

    def get_goods_url(self, category_hook):
        """
        Метод для получения списка ссылок на товары для категории с учетом пагенации.
        :param category_hook: url ссылка на категорию из каталога.
        """
        goods_url = []
        response = requests.get(category_hook)
        if response.status_code in [404, 502, 403]:
            return goods_url

        html = etree.HTML(response.text)
        max_page = int(html.xpath('//ul[@class="ul-cat-pager"]/li/a/@href')[-1].split('=')[-1])
        i = 1
        while i <= max_page:
            response = requests.get(category_hook + 'index.php?PAGEN_3=' + str(i))
            urls = etree.HTML(response.text)
            i += 1
            for url in urls.xpath('//a[@class="img_href"]'):
                link = url.xpath('@href')[0]
                goods_url.append('https://www.maxidom.ru' + str(link))
        time.sleep(0.2)
        return goods_url

    def get_item_data(self, good_url):
        """
        Метод получения характеристик товара
        :param good_url: ссылка на товар
        """
        response = requests.get(good_url)
        if response.status_code in [404, 502, 403]:
            return None
        data = etree.HTML(response.text)

        product_id = data.xpath('//span[@class="small-country"]')[0].text.split(' ')[-1]
        product = data.xpath('//div[@class="maxi_container"]/h1')[0].text
        product_url = good_url
        nominal_price = data.xpath('//div[@id="mnogo_prd_price"]/@data-repid_price')[0]
        unit = data.xpath('//div[@class="pack"]')[0].text
        manufacturer = data.xpath('//span[@class="value"]')[0].text.split()[0] + \
                       data.xpath('//span[@class="value"]')[0].text.split()[1]
        image_urls = data.xpath('//a[@id="product-image"]')[0].attrib['href']
        description = data.xpath('//p[@style="line-height: 19px;"]')[0].text
        extra_data = data.xpath('//section[@id="product-technicals"]/div[@class="tab-row"]')
        width = data.xpath('//span[@class="value"]')[1].text.split()[0] + \
                data.xpath('//span[@class="value"]')[1].text.split()[1]
        if all((
               product_id, product, product_url, nominal_price, unit, manufacturer, image_urls, description, extra_data,
               width)):
            good_data = {
                "product_id": product_id,
                "product": product,
                "product_url": product_url,

                "old_price": None,
                "price": int(nominal_price),
                "currency": 'RUB',
                "unit": unit,
                "quantity": 1,
                "is_available": True,

                "vendor": manufacturer,
                "image_url": 'https://www.maxidom.ru' + image_urls,
                "description": description,
                "extra_data": {
                    i.xpath('span')[0].text: i.xpath('span')[1].text for i in extra_data
                },

                "length": 0,
                "width": width,
                "height": 0,
                "weight": 0,
            }
            return good_data

    def get_goods_price(self, category_hook):
        """
        Метод обновления цен товаров в категории
        :param category_hook: ссылка на категорию
        """

        result_dict = {
            'price_dict': {},
            'is_stable': True,
        }
        price_dict = {}
        response = requests.get(category_hook)
        if response.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif response.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict
        html = etree.HTML(response.text)
        max_page = int(html.xpath('//ul[@class="ul-cat-pager"]/li/a/@href')[-1].split('=')[-1])
        i = 1
        while i <= max_page:
            response = requests.get(category_hook + 'index.php?PAGEN_3=' + str(i))
            prices = etree.HTML(response.text)
            i += 1
            for price in prices.xpath('//article[@class="item-list group"]'):
                product_id = price.xpath('div[2]/div[1]/small[2]')[0].text.split(' ')[-1]
                nominal_price = int(price.xpath('div[3]/div[1]/span[2]/span[1]/@data-repid_price')[0])
                price_dict[product_id] = {
                    'nominal_price': nominal_price,
                    'old_price': None
                }
        result_dict['price_dict'] = price_dict
        return result_dict

    def get_categories_data(self, catalog_hook):
        """
        Функция для получения всех подкатегорий
        :param catalog_hook: ссылка страницы с каталогом

        """
        result = {
            'name': "Maxidom",
            'url': catalog_hook,
            'children': [],
            'is_stable': True,
        }
        response = requests.get(catalog_hook)
        if response.status_code in [404]:
            result['is_stable'] = True
            return result
        elif response.status_code in [502, 403]:
            result['is_stable'] = False
            return result
        data = etree.HTML(response.text)
        categories = data.xpath('//div[@class="wrap-left"]/nav/ul/li/div/a')
        for item in categories[24:25]:
            category_name = item.xpath('span')[0].text.strip()
            category_url = 'https://www.maxidom.ru' + str(item.xpath('@href')[0])
            if 'Бренды' in category_name:
                result['children'].append({
                    "name": category_name,
                    "url": category_url,
                    "children": self._get_brands_children(category_url),
                })
            else:
                result['children'].append({
                    "name": category_name,
                    "url": category_url,
                    "children": self._get_children(item),
                })
        return result

    def _get_children(self, item):
        """
        Функция для получения всех дочерних категории подкатегории
        :param item: xpath запрос на конкретную категорию
        """
        categories = item.xpath('../../div[2]/ul/li/a')
        categories_list = []
        for item in categories:
            category_name = item.text
            category_url = 'https://www.maxidom.ru' + str(item.xpath('@href')[0])
            result = {
                "name": category_name,
                "url": category_url,
                'children': [],
                'is_stable': True,
            }
            response = requests.get(category_url)
            data = etree.HTML(response.text)
            categories_list.append(result)
            for item in data.xpath('//nav[@class="nav-filter"]/ul/li/a'):
                category_name = item.text.strip()
                if 'Показать все' in category_name or 'Свернуть категории' in category_name:
                    continue
                if item.xpath('@href'):
                    category_url = 'https://www.maxidom.ru' + str(item.xpath('@href')[0])
                result['children'].append({
                    "name": category_name,
                    "url": category_url,
                    'children': [],
                    'is_stable': True,
                })
        return categories_list

    def _get_brands_children(self, brands_url):
        """
        Функция для получения всех дочерних категории 'бренды' и ее подкатегории
        :param brands_url: ссылка категории 'бренды'
        """
        response = requests.get(brands_url)
        data = etree.HTML(response.text)
        categories_list = []
        for item in data.xpath('//div[@class="brands_alphabetical-list"]/div'):
            for brand in item.xpath('div/span'):
                category_name = brand.xpath('a')[0].text
                category_url = 'https://www.maxidom.ru' + str(brand.xpath('a/@href')[0])
                result = {
                    "name": category_name,
                    "url": category_url,
                    'children': [],
                    'is_stable': True,
                }
                response = requests.get(category_url)
                data = etree.HTML(response.text)
                categories_list.append(result)
                for category in data.xpath('//nav[@class="nav-filter"]/ul/li/a'):
                    category_name = category.text.strip()
                    if 'Показать все' in category_name or 'Свернуть категории' in category_name:
                        continue
                    if category.xpath('@href'):
                        category_url = 'https://www.maxidom.ru' + str(category.xpath('@href')[0])
                    result['children'].append({
                        "name": category_name,
                        "url": category_url,
                        'children': [],
                        'is_stable': True,
                    })
            return categories_list
