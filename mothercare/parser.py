import requests
from lxml import etree


class MotherCareParser:
    """
           Парсер товаров площадки maxidom: maxidom.ru

        """

    origin = 'mothercare.ru'
    HEADERS = {'authority': ''}

    # хук каталога
    catalog_hook = "https://www.mothercare.ru"
    site_url = "https://www.mothercare.ru"
    # пример определенного хука каталога
    catalog_hook_example = 'https://www.mothercare.ru/ru/одежда-для-самых-маленьких-1747.html'

    cookies = {
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.mothercare.ru',
        'Connection': 'keep-alive',
        'TE': 'Trailers',
    }

    def get_sub_categories(self, catalog_hook):
        """
        Функция для получения подкатегорий
        :param catalog_hook: ссылка на родительскую категорию

        """
        result = {
            'name': "Mothercare",
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
        categories_list = []
        category = data.xpath(f"//a[@class='level0'][@href='{catalog_hook}']/../ul/li/div/div/ul/li/a")
        # 1 подкатегория отличается от всез остальных, поэтому делаем тут проверку и отправляес нужный запрос
        if not category:
            category = data.xpath(f"//a[@class='level0 no-border'][@href='{catalog_hook}']/../ul/li/div/div/ul/li/a")
        for item in category:
            if item.text and item.text.strip():
                category_name = item.text
            elif item.xpath('b/font'):
                category_name = item.xpath('b/font')[0].text
            elif item.xpath('b'):
                category_name = item.xpath('b')[0].text
            elif item.xpath('p'):
                category_name = category[1].xpath('p')[0].text
            elif item.xpath('img'):
                category_name = str(item.xpath('img/@alt')[0])
            else:
                continue
            category_url = str(item.xpath('@href'))
            # в некоторыз ссылках нет домена сайте, делаем проверку и если нет домена, то его добавляем
            if not 'www.mothercare.ru' in category_url:
                category_url = 'www.mothercare.ru' + category_url.replace('[', '').replace(']', '').replace("'", '')
            categories_list.append({
                "name": category_name,
                "url": category_url,
                "children": None,
            })
        return categories_list

    def get_goods_url(self, category_hook):
        """
        Метод для получения списка ссылок на товары для категории с учетом пагенации.
        :param category_hook: url ссылка на категорию из каталога.
        """
        goods_url = []
        i = 1

        while True:
            response = requests.get(category_hook + f'?p={str(i)}')
            if response.status_code in [404, 502, 403]:
                return goods_url
            data = etree.HTML(response.text)
            for item in data.xpath('//li[@itemtype="http://schema.org/Product"]/a/@href'):
                url = str(item)
                goods_url.append(url)
            # Пробуем взять следующую страницу, если нет, то возвращаем что уже получено
            try:
                next_page = data.xpath('//a[@rel="next"]')[0].attrib['href']
                i += 1
            except IndexError:
                return goods_url

    def get_item_data(self, good_url):
        """
        Метод получения характеристик товара
        :param good_url: ссылка на товар
        """
        goods_data = []
        response = requests.get(good_url)
        if response.status_code in [404, 502, 403]:
            return None
        data = etree.HTML(response.text)
        data_id = data.xpath('//*[@id="entity-id"]/@value')[0]
        data_headers = {
            'id': f'{str(data_id)}',
        }
        response = requests.post('https://www.mothercare.ru/ru/ajax/product/', headers=self.headers,
                                 cookies=self.cookies,
                                 data=data_headers)
        html = etree.HTML(response.text)
        size_data = html.xpath('//select[@id="sizeOption"]/option')
        size_dict = {}
        for item in size_data:
            if not item.text == 'Размер':
                price = int(item.xpath('@price')[0])
                size_dict[item.text] = price
            else:
                continue
        size_list = html.xpath('//ul[@class="age-list"]/li/div/div/span')
        # Проверяем size_list, если пустой, значит этот товар без размеров, а для таких товаров вызываем другой метод
        if not size_list:
            return self._get_item_data_without_size(good_url)
        i = 1
        # while нужен для того чтобы вернуть столько товаров сколько у этого товара есть размеров с их ценами
        while i <= len(size_dict):
            product_id = data.xpath('//div[@class="item-code"]/br')[0].tail.strip()
            product = data.xpath('//div[@class="product-display-image"]/h1')[0].text
            product_url = good_url
            size = size_list[i - 1].text
            nominal_price = size_dict.get(size)
            unit = '1 шт'
            manufacturer = data.xpath('//span[@property="brand"]')[0].text
            image_urls = []
            image_urls.append(str(data.xpath('//a[@class="active"]/@href')[0]))
            for picture in data.xpath('//div[@class="item"]/a/@href'):
                image_urls.append(str(picture))
            description = data.xpath('//span[@property="description"]/p')[0].text
            extra_data = data.xpath('//div[@class="panel-collapse panel-collapse-block"]/div/div/ul/li')
            if all((product_id, product, product_url, nominal_price, unit, manufacturer, image_urls, description,
                    extra_data,)):
                good_data = {
                    "product_id": product_id,
                    "product": product,
                    "product_url": product_url,

                    "old_price": None,
                    "size": size,
                    "price": int(nominal_price),
                    "currency": 'RUB',
                    "unit": unit,
                    "quantity": 1,
                    "is_available": True,

                    "vendor": manufacturer,
                    "image_url": image_urls,
                    "description": description,
                    "extra_data": {
                        i.text.split(':')[0]: i.xpath('span')[0].text for i in extra_data
                    },

                    "length": 0,
                    "width": 0,
                    "height": 0,
                    "weight": 0,
                }
                i += 1
                goods_data.append(good_data)
        return goods_data

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
        i = 1
        while True:
            response = requests.get(category_hook + f'?p={str(i)}')
            html = etree.HTML(response.text)
            if response.status_code in [404]:
                result_dict['is_stable'] = True
                return result_dict
            elif response.status_code in [502, 403]:
                result_dict['is_stable'] = False
                return result_dict
            i = 1
            for item in html.xpath('//li[@itemtype="http://schema.org/Product"]/a/@href'):
                response = requests.get(str(item))
                data = etree.HTML(response.text)
                product_id = data.xpath('//div[@class="item-code"]/br')[0].tail.strip()
                nominal_price = data.xpath('//div[@class="price current-price"]')[0].text.split('руб')[
                    0].strip().replace(' ', '')
                # if проверяет четырехзначное ли чило и есть ли промежуток между числами
                if len(list(nominal_price.split('-'))) > 1 and len(list(nominal_price.split('-')[1])) > 3:
                    nominal_price = nominal_price.split('-')[1]
                # if проверяет трехзначное ли чило и есть ли промежуток между числами
                elif len(list(nominal_price.split('-'))) > 1 and len(list(nominal_price.split('-')[1])) < 4:
                    nominal_price = nominal_price.split('-')[1]
                price_dict[product_id] = {
                    'nominal_price': nominal_price,
                    'old_price': None
                }
                result_dict['price_dict'] = price_dict
            # Пробуем взять следующую страницу, если нет, то возвращаем что уже получено
            try:
                next_page = html.xpath('//a[@rel="next"]')[0].attrib['href']
                i += 1
            except IndexError:
                return result_dict

    def _get_item_data_without_size(self, good_url):
        """
        Метод получения характеристик товара без размеров
        :param good_url: ссылка на товар
        """
        response = requests.get(good_url)
        if response.status_code in [404, 502, 403]:
            return None
        data = etree.HTML(response.text)
        product_id = data.xpath('//div[@class="item-code"]/br')[0].tail.strip()
        product = data.xpath('//div[@class="product-display-image"]/h1')[0].text
        product_url = good_url
        nominal_price = data.xpath('//div[@class="price current-price"]/@content')[0]
        # if проверяет четырехзначное ли чило и если да то удаляет лишние пробелы для переобразования его в int
        if len(nominal_price.split(' ')) > 1:
            nominal_price = nominal_price.split(' ')[0] + nominal_price.split(' ')[1]
        unit = '1 шт'
        manufacturer = data.xpath('//span[@property="brand"]')[0].text
        image_urls = []
        image_urls.append(str(data.xpath('//a[@class="active"]/@href')[0]))
        for picture in data.xpath('//div[@class="item"]/a/@href'):
            image_urls.append(str(picture))
        description = data.xpath('//span[@property="description"]/p')[0].text
        extra_data = data.xpath('//div[@class="panel-collapse panel-collapse-block"]/div/div/ul/li')
        if all((product_id, product, product_url, nominal_price, unit, manufacturer, image_urls, description,
                extra_data,)):
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
                "image_url": image_urls,
                "description": description,
                "extra_data": {
                    i.text.split(':')[0]: i.xpath('span')[0].text for i in extra_data if i.xpath('span')
                },

                "length": 0,
                "width": 0,
                "height": 0,
                "weight": 0,
            }
            return good_data

    def get_categories_data(self, catalog_hook):
        """
        Функция для получения всех подкатегорий
        :param catalog_hook: ссылка на родительскую категорию

        """
        result = {
            'name': "Mothercare",
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
        categories = data.xpath('//li[contains(@class, "level0")]')

        result['children'].append(self._get_0_category(categories[0]))
        result['children'].append(self._get_1_2_4_category(categories[1]))
        result['children'].append(self._get_1_2_4_category(categories[2]))
        result['children'].append(self._get_3_7_8_category(categories[3]))
        result['children'].append(self._get_1_2_4_category(categories[4]))
        result['children'].append(self._get_5_6_category(categories[5]))
        result['children'].append(self._get_5_6_category(categories[6]))
        result['children'].append(self._get_3_7_8_category(categories[7]))
        result['children'].append(self._get_3_7_8_category(categories[8]))
        result['children'].append(self._get_9_10_category(categories[9]))
        result['children'].append(self._get_9_10_category(categories[10]))
        return result

    def get_children(self, parent_xpath, item):
        if 'banner' in parent_xpath.attrib['class']:
            return []
        childs = {}
        main_child = []
        previews = None
        for li in parent_xpath.xpath('ul/li'):
            try:
                _class = li.attrib['class']
            except:
                continue
            if 'level1' in _class:
                if not li.xpath('a/b/text()'):
                    continue
                previews = str(li.xpath('a/b/text()')[0])
                continue

            try:
                name = li.xpath('a/b|*/text()')[0].text
            except:
                if li.xpath('a/*/text()'):
                    name = str(li.xpath('a/*/text()')[0])
                else:
                    if li.xpath('p/a'):
                        name = li.xpath('p/a')[0].text
                    else:
                        name = str(li.xpath('a/text()')[0])
            if 'pleft' in _class:
                if not previews:
                    previews = parent_xpath.xpath('ul/li/p')[0].text
                    childs.update({previews: {
                        'name': previews,
                        'url': li.xpath('a')[0].attrib['href'],
                        'children': []
                    }})
                    continue
                if previews in childs:
                    childs[previews]['children'].append({
                        'name': name,
                        'url': li.xpath('a')[0].attrib['href'],
                        'children': []
                    })
                else:
                    childs.update({previews: {
                        'name': name,
                        'url': li.xpath('a')[0].attrib['href'],
                        'children': []
                    }})
            else:
                if 'first' in _class and 'parent' in _class:
                    previews = name
                if li.xpath('p/a/@href'):
                    url = li.xpath('p/a/@href')[0]
                else:
                    url = li.xpath('a')[0].attrib['href']
                childs.update({
                    'name': name,
                    'url': url,
                    'children': []
                })
                previews = name

        result = [{k: v} for k, v in childs.items()]
        result.extend(main_child)
        return result

    # for 5, 6
    def _get_5_6_category(self, node):  # for 5, 6

        def get_category(uls):
            data = {}
            for ul in uls:
                last = None
                for li in ul.xpath('li'):
                    if li.xpath('p') and (li.xpath('p')[0].text == 'Наши рекомендации' or li.xpath('p')[
                        0].text == 'обратите внимание'):
                        continue
                    _class = li.attrib['class']
                    sub_category_url = li.xpath('a')[0].attrib['href']
                    if li.xpath('a/b/font'):
                        sub_category_name = li.xpath('a/b/font')[0].text
                    else:
                        if li.xpath('a/b'):
                            sub_category_name = li.xpath('a/b')[0].text
                        else:
                            sub_category_name = li.xpath('a')[0].text
                    if 'Магазин' in sub_category_name or 'Акции' in sub_category_name:
                        continue
                    if 'pleft' in _class:
                        data[last]['children'].append({
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        })
                    else:
                        data[sub_category_name] = {
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        }
                        last = sub_category_name
            return data

        category_name = node.xpath('a')[0].text
        category_url = str(node.xpath('a/@href')[0])
        columns = node.xpath('ul/li[@class="nav-dropdown"]/div/div')
        data = []
        for column in columns:
            if column.xpath('ul/li/ul'):
                categories = get_category(column.xpath('ul/li/ul'))
            else:
                categories = get_category(column.xpath('ul'))
            data.append(categories)
        data = data[:3]
        result = []
        for i in data:
            for _, v in i.items():
                result.append(v)
        return {
            'name': category_name,
            'url': category_url,
            'children': result,
            'is_stable': True
        }

    # for 3, 7, 8
    def _get_3_7_8_category(self, node):

        def get_category(uls):
            data = {}
            for ul in uls:
                last = None
                for li in ul.xpath('li'):
                    if li.xpath('p') and (li.xpath('p')[0].text == 'Наши рекомендации' or li.xpath('p')[
                        0].text == 'обратите внимание'):
                        continue
                    _class = li.attrib['class']
                    if li.xpath('p/a'):
                        sub_category_url = li.xpath('p/a')[0].attrib['href']
                    else:
                        sub_category_url = li.xpath('a')[0].attrib['href']
                    if li.xpath('a/b/font'):
                        sub_category_name = li.xpath('a/b/font')[0].text
                    else:
                        if li.xpath('a/b'):
                            sub_category_name = li.xpath('a/b')[0].text
                        else:
                            if li.xpath('p/a'):
                                sub_category_name = li.xpath('p/a')[0].text
                            else:
                                sub_category_name = li.xpath('a')[0].text
                    if 'Магазин' in sub_category_name or 'Акции' in sub_category_name:
                        continue
                    if 'pleft' in _class:
                        data[last]['children'].append({
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        })
                    else:
                        data[sub_category_name] = {
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        }
                        last = sub_category_name
            return data

        category_name = node.xpath('a')[0].text
        category_url = str(node.xpath('a/@href')[0])
        columns = node.xpath('ul/li[@class="nav-dropdown"]/div/div')
        data = []
        for column in columns:
            if column.xpath('ul/li/ul'):
                categories = get_category(column.xpath('ul/li/ul'))
            else:
                categories = get_category(column.xpath('ul'))
            data.append(categories)
        # data = data[:3]
        result = []
        for i in data:
            for _, v in i.items():
                result.append(v)
        return {
            'name': category_name,
            'url': category_url,
            'children': result[:-1],
            'is_stable': True
        }

    # for 1, 2, 4
    def _get_1_2_4_category(self, node):

        def get_category(uls):
            data = {}
            for ul in uls:
                last = last_link = None
                for li in ul.xpath('li'):
                    if li.xpath('p') and (li.xpath('p')[0].text == 'Наши рекомендации' or li.xpath('p')[
                        0].text == 'обратите внимание'):
                        continue
                    _class = li.attrib['class']
                    if li.xpath('p/a'):
                        sub_category_url = li.xpath('p/a')[0].attrib['href']
                    else:
                        if li.xpath('a'):
                            sub_category_url = li.xpath('a')[0].attrib['href']
                        else:
                            continue
                    if li.xpath('a/b/font'):
                        sub_category_name = li.xpath('a/b/font')[0].text
                    else:
                        if li.xpath('a/b'):
                            sub_category_name = li.xpath('a/b')[0].text
                        else:
                            if li.xpath('p/a'):
                                sub_category_name = li.xpath('p/a')[0].text
                            else:
                                sub_category_name = li.xpath('a')[0].text
                    if 'Магазин' in sub_category_name or 'Акции' in sub_category_name:
                        continue
                    if 'pleft' in _class:
                        if sub_category_name == 'Подушки для кормления':
                            data[sub_category_name] = {
                                'name': sub_category_name,
                                'url': sub_category_url,
                                'children': [],
                            }
                            continue
                        data[last]['children'].append({
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        })
                    else:
                        data[sub_category_name] = {
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        }
                        last, last_link = sub_category_name, sub_category_url
            return data

        category_name = node.xpath('a')[0].text
        category_url = str(node.xpath('a/@href')[0])
        columns = node.xpath('ul/li[@class="nav-dropdown"]/div/div')
        data = []
        for column in columns:
            if column.xpath('ul/li/ul'):
                categories = get_category(column.xpath('ul/li/ul'))
            else:
                categories = get_category(column.xpath('ul'))
            data.append(categories)
        # data = data[:3]
        result = []
        for i in data:
            for _, v in i.items():
                result.append(v)
        i = 1
        if len(result) == 29:
            i = 2
        return {
            'name': category_name,
            'url': category_url,
            'children': result[:-i],
            'is_stable': True
        }

    # for 9, 10
    def _get_9_10_category(self, node):

        def get_category(uls):
            data = {}
            for ul in uls:
                last = None
                for li in ul.xpath('li'):
                    if li.xpath('p') and (li.xpath('p')[0].text == 'Наши рекомендации' or li.xpath('p')[
                        0].text == 'обратите внимание'):
                        continue
                    _class = li.attrib['class']
                    if li.xpath('p/a'):
                        sub_category_url = li.xpath('p/a')[0].attrib['href']
                    else:
                        if li.xpath('a'):
                            sub_category_url = li.xpath('a')[0].attrib['href']
                        else:
                            continue
                    if li.xpath('a/b/font'):
                        sub_category_name = li.xpath('a/b/font')[0].text
                    else:
                        if li.xpath('a/b'):
                            sub_category_name = li.xpath('a/b')[0].text
                        else:
                            if li.xpath('p/a'):
                                sub_category_name = li.xpath('p/a')[0].text
                            else:
                                if li.xpath('a/p'):
                                    sub_category_name = li.xpath('a/p')[0].text
                                else:
                                    sub_category_name = li.xpath('a')[0].text
                    if 'Магазин' in sub_category_name or 'Акции' in sub_category_name or sub_category_name in 'Как выбрать автокресло?':
                        continue
                    if 'pleft' in _class:
                        data[last]['children'].append({
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        })
                    else:
                        data[sub_category_name] = {
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        }
                        last = sub_category_name
            return data

        category_name = node.xpath('a')[0].text
        category_url = str(node.xpath('a/@href')[0])
        columns = node.xpath('ul/li[@class="nav-dropdown"]/div/div')
        data = []
        for column in columns:
            if column.xpath('ul/li/ul'):
                categories = get_category(column.xpath('ul/li/ul'))
            else:
                categories = get_category(column.xpath('ul'))
            data.append(categories)
        # data = data[:3]
        result = []
        for i in data:
            for _, v in i.items():
                result.append(v)
        return {
            'name': category_name,
            'url': category_url,
            'children': result[:-2],
            'is_stable': True
        }

    def _get_0_category(self, node):

        def get_category(uls):
            data = {}
            for ul in uls:
                last = None
                for li in ul.xpath('li'):
                    if li.xpath('p') and (li.xpath('p')[0].text == 'Наши рекомендации' or li.xpath('p')[
                        0].text == 'обратите внимание'):
                        continue
                    _class = li.attrib['class']
                    if li.xpath('p/a'):
                        sub_category_url = li.xpath('p/a')[0].attrib['href']
                    else:
                        if li.xpath('a'):
                            sub_category_url = li.xpath('a')[0].attrib['href']
                        else:
                            continue
                    if li.xpath('a/b/font'):
                        sub_category_name = li.xpath('a/b/font')[0].text
                    else:
                        if li.xpath('a/b'):
                            sub_category_name = li.xpath('a/b')[0].text
                        else:
                            if li.xpath('p/a'):
                                sub_category_name = li.xpath('p/a')[0].text
                            else:
                                if li.xpath('a/p'):
                                    sub_category_name = li.xpath('a/p')[0].text
                                else:
                                    sub_category_name = li.xpath('a')[0].text
                    if 'Магазин' in sub_category_name or 'Акции' in sub_category_name or sub_category_name in 'Особенности выбора одежды для новорожденных':
                        continue
                    if 'pleft' in _class and last:
                        data[last]['children'].append({
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        })
                    else:
                        data[sub_category_name] = {
                            'name': sub_category_name,
                            'url': sub_category_url,
                            'children': [],
                        }
                        if 'first' in _class or 'level2 nav-1-1-12' in _class:
                            last = sub_category_name
            return data

        category_name = node.xpath('a')[0].text
        category_url = str(node.xpath('a/@href')[0])
        columns = node.xpath('ul/li[@class="nav-dropdown"]/div/div')
        data = []
        for column in columns:
            if column.xpath('ul/li/ul'):
                categories = get_category(column.xpath('ul/li/ul'))
            else:
                categories = get_category(column.xpath('ul'))
            data.append(categories)
        # data = data[:3]
        result = []
        for i in data:
            for _, v in i.items():
                result.append(v)
        return {
            'name': category_name,
            'url': category_url,
            'children': result[:-1],
            'is_stable': True
        }

