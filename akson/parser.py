import json
import re

import requests


class AksonParser:
    """
    Парсер товаров площадки Akson: akson.ru

    """

    origin = 'akson.ru'
    HEADERS = {'authority': ''}

    # хук каталога
    catalog_hook = "https://akson.ru/"
    site_url = "https://akson.ru/"

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
        # Отделяем нужную часть json от js
        json_object = re.search(r"__INITIAL_STATE__=(.*);\(function", response.text)[1]
        # Отделенную часть js переобразовываем в json
        content_json = json.loads(json_object)
        categories_list = content_json['Sections']['catalogSection']['children']
        if not categories_list:
            categories_list = [content_json['Sections']['catalogSection']['code']]
        # Циклом берем подкатегории категории и проходимся по ним
        for category in categories_list:
            # Бывают категории без подкатегории, тут это проверяем, сначала пробуем брать с категорией, потом без
            try:
                link_to_goods = f"https://api1.akson.ru:8443/v8/catalog/section_products/{category['code']}/50/0/"
            except TypeError:
                link_to_goods = f"https://api1.akson.ru:8443/v8/catalog/section_products/{category}/50/0/"
            response = requests.get(link_to_goods)
            data = json.loads(response.text)
            # источник нам возвращает в json категории в которых нет товаров, проверям тут, если есть товары то берем их
            if data['data']['products']:
                for good in data['data']['products']:
                    product_id = good['id']
                    nominal_price = good['price']
                    price_dict[product_id] = {
                        'nominal_price': nominal_price,
                        'old_price': None
                    }
            else:
                continue
        result_dict['price_dict'] = price_dict
        return result_dict

    def get_item_data(self, good_url):
        """
        Метод получения характеристик товара
        :param good_url: ссылка на товар
        """
        response = requests.get(good_url)
        if response.status_code in [404, 502, 403]:
            return None
        # Отделяем нужную часть json от js
        json_object = re.search(r"__INITIAL_STATE__=(.*);\(function", response.text)[1]
        content_json = json.loads(json_object)
        # Получаем id товара
        id_for_good = content_json['Products']['product']['products'][0]['id']
        # И передаем его методу, чтобы он получил json товара
        goods_data = self._get_good_data(id_for_good)

        product_id = goods_data['data'][0]['id']
        product = goods_data['data'][0]['name']
        product_url = 'https://akson.ru/p/' + goods_data['data'][0]['code']
        nominal_price = goods_data['data'][0]['price']
        unit = str(goods_data['data'][0]['inPack']) + goods_data['data'][0]['unit']
        manufacturer = goods_data['data'][0]['brand']
        image_urls = 'https://akson.ru' + goods_data['data'][0]['detailImage']
        description = goods_data['data'][0]['detailText']
        extra_data = goods_data['data'][0]['newProps']
        weight = str(goods_data['data'][0]['weight']) + 'кг'
        length = goods_data['data'][0]['packLength']
        height = goods_data['data'][0]['packHeight']
        width = goods_data['data'][0]['packWidth']
        if all((product_id, product, product_url, nominal_price, unit, manufacturer, image_urls, description, width)):
            good_data = {
                "product_id": product_id,
                "product": product,
                "product_url": product_url,

                "old_price": None,
                "price": nominal_price,
                "currency": 'RUB',
                "unit": unit,
                "quantity": 1,
                "is_available": True,

                "vendor": manufacturer,
                "image_url": 'https://www.maxidom.ru' + image_urls,
                "description": description,
                "extra_data": {
                    extra_data[i]['name']: extra_data[i].get('value') for i in list(extra_data)
                },

                "length": length,
                "width": width,
                "height": height,
                "weight": weight,
            }
            return good_data

    def get_goods_url(self, category_hook):
        """
        Метод получения всех ссылок на товары с определнной подкатегории
        :param category_hook: id товара
        """
        goods_url = []
        response = requests.get(category_hook)
        if response.status_code in [404, 502, 403]:
            return goods_url
        # Отделяем нужную часть json от js
        json_object = re.search(r"__INITIAL_STATE__=(.*);\(function", response.text)[1]
        # Отделенную часть js переобразовываем в json
        content_json = json.loads(json_object)
        categories_list = content_json['Sections']['catalogSection']['children']
        if not categories_list:
            categories_list = [content_json['Sections']['catalogSection']['code']]
        # Циклом берем подкатегории категории и проходимся по ним
        for category in categories_list:
            # Бывают категории без подкатегории, тут это проверяем, сначала пробуем брать с категорией, потом без
            try:
                link_to_goods = f"https://api1.akson.ru:8443/v8/catalog/section_products/{category['code']}/50/0/"
            except TypeError:
                link_to_goods = f"https://api1.akson.ru:8443/v8/catalog/section_products/{category}/50/0/"
            response = requests.get(link_to_goods)
            data = json.loads(response.text)
            # источник нам возвращает в json категории в которых нет товаров, проверям тут, если есть товары то берем их
            if data['data']['products']:
                for good in data['data']['products']:
                    link = good['code']
                    goods_url.append('https://akson.ru/p/' + link)
            else:
                continue
        return goods_url

    def _get_good_data(self, good_id):
        """
        Метод получения данных товара
        :param good_id: id товара
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'AUTHORIZATION': '',
            'X-AKSON-STORE': '50',
            'X-AKSON-PLATFORM': 'desktop',
            'X-AKSON-SID': 'retail',
            'X-AKSON-SUPPORT-APPLEPAY': '0',
            'X-AKSON-IS-TEST-MODE': '',
            'Origin': 'https://akson.ru',
            'Connection': 'keep-alive',
        }

        params = (
            ('ids[]', [good_id]),
        )

        response = requests.get('https://api1.akson.ru:8443/v2/catalog/products/50/0/', headers=headers, params=params)
        return response.json()

    def get_categories_data(self, catalog_hook):
        """
        Функция для получения всех подкатегорий
        :param catalog_hook: ссылка страницы с каталогом

        """
        result = {
            'name': "Akson",
            'url': catalog_hook,
            'children': [],
            'is_stable': True,
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'AUTHORIZATION': '',
            'X-AKSON-STORE': '50',
            'X-AKSON-PLATFORM': 'desktop',
            'X-AKSON-SID': 'retail',
            'X-AKSON-SUPPORT-APPLEPAY': '0',
            'X-AKSON-DEVICE-UUID': 'a6927db9-e7b2-4dee-974e-e10bf8777c99',
            'X-AKSON-IS-TEST-MODE': '',
            'Origin': catalog_hook,

        }
        response = requests.get('https://api1.akson.ru:8443/v4/catalog/menu/0/50/0/', headers=headers)
        if response.status_code in [404]:
            result['is_stable'] = True
            return result
        elif response.status_code in [502, 403]:
            result['is_stable'] = False
            return result

        data = response.json()
        for item in data['data']['topMenu']:
            category_name = item['name']
            category_url = 'https://akson.ru/c/' + item['code']
            result['children'].append({
                "name": category_name,
                "url": category_url,
                "children": self._get_children(item),
            })
        return result

    def _get_children(self, children):
        """
        Функция для получения всех дочерних категории подкатегории
        :param children: дикт
        """
        categories_list = []
        for item in children['children']:
            category_name = item['name']
            category_url = 'https://akson.ru/c/' + item['code']
            result = {
                "name": category_name,
                "url": category_url,
                'is_stable': True,
                'children': [],
            }
            for subcategory in item['children']:
                category_name = subcategory['name']
                category_url = 'https://akson.ru/c/' + subcategory['code']
                result['children'].append({
                    "name": category_name,
                    "url": category_url,
                    'is_stable': True,
                    'children': [],
                })
            print(categories_list)
            categories_list.append(result)
        return categories_list
