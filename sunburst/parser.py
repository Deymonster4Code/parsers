import re
import time
from datetime import datetime

import requests
from lxml import etree


# class SunburstEvent(GenericParser):
class SunburstEvent:
    """
    Парсер для площадки https://sunburst.live/tickets.
    """

    PARSER_NAME = "sunburst.live"
    EVENTS_HOOK_HELP = 'Пример, https://sunburst.live/tickets'
    TICKETS_HOOK_HELP = "Пример, https://sunburst.live/tickets"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Origin': 'https://sunburst.live',
        'Referer': 'https://sunburst.live/tickets',
    }
    HEADERS_TILDACDN = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://sunburst.live',
        'Referer': 'https://sunburst.live/tickets',
        'TE': 'Trailers',
    }

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        response = requests.get(hook, headers=self.HEADERS_TILDACDN)
        if not response.status_code == 200:
            return result
        html = etree.HTML(response.text)
        for concert in html.xpath('//div[@class="t744__textwrapper"]'):
            if all((
                   self._get_event_title(concert), self._get_event_date(concert, 0), self._get_event_date(concert, 1))):
                result.append({
                    "event_hook": 'https://sunburst.live/tickets',
                    "event_name": self._get_event_title(concert),
                    "event_starts_at": datetime.strptime(self._get_event_date(concert, 0), '%d.%m.%Y %H:%M '),
                    "event_end_at": datetime.strptime(self._get_event_date(concert, 1), ' %d.%m.%Y %H:%M'),
                })
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов c конкретного мероприятия.

        Args:
            seance_hook: (str) принимает ссылку определенного мероприятия

        Returns:
            (dict)
        """
        result = {}
        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        response = requests.get(seance_hook, headers=self.HEADERS_TILDACDN)
        html = etree.HTML(response.text)
        products_id = []
        for item in html.xpath('//div[@class="t744"]'):
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            product_id = item.xpath(
                'div[@class="t-container js-product js-product-single js-store-product js-store-product_single"]')[
                0].attrib['data-product-gen-uid']
            data = item.xpath('div/div/div/div/div/div[@class="t744__title t-name t-name_xl js-product-name"]')
            sector_name = data[0].text.replace('\n', '')
            result.update({product_id: {
                'seat_id': product_id,
                'sector_name': sector_name,
                'nominal_price': None,
                'currency': 'rub',
                'qty_available': 1,
                'is_multiple': True,
            }})
            products_id.append(product_id)
        params = (
            ('productsuid[]', products_id),
        )
        response = requests.get('https://store.tildacdn.com/api/getproductsbyuid/', headers=self.HEADERS, params=params)
        for product in response.json()['products']:
            result[product['uid']]['nominal_price'] = int(product['price'].split('.')[0])
        result_dict['tickets'] = list(result.values())
        return result_dict

    def _get_event_title(self, soup):
        """Получение название мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        data = soup.xpath('div/div[@class="t744__title t-name t-name_xl js-product-name"]')
        a = data[0].text.replace('\n', '')
        return a

    def _get_event_date(self, soup, index):
        """Получение даты мероприяте.

        Args:
            soup: (str) принимает текст
            index: (int) принимает число

        Returns:
            (str)
        """
        text = soup.xpath('div[@class="t744__descr t-descr t-descr_xxs"]')[0].text
        result = re.search(r"\s*(\d+.\d+.\d+\s*\d+:\d+\s*-\s*\d+.\d+.\d+\s*\d+:\d+)", text)
        if result:
            return result[1].split('-')[index]
