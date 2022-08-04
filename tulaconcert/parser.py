import re

import requests
from lxml import etree
from datetime import datetime
from arrow.locales import RussianLocale
import logging


logger = logging.getLogger(__name__)



class TulaConcert:
    """
            Парсер для площадки https://xn--80akocmfqjhc2b.xn--p1ai/  (тулаконцерт.рф)
            """

    PARSER_NAME = "tulaconcert"
    EVENTS_HOOK_HELP = 'Пример, https://xn--80akocmfqjhc2b.xn--p1ai/'
    TICKETS_HOOK_HELP = "Пример, https://xn--80akocmfqjhc2b.xn--p1ai/"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'host': 'xn--80akocmfqjhc2b.xn--p1ai'
    }

    url = 'https://xn--80akocmfqjhc2b.xn--p1ai'

    client_key = '0a3b0c31-0c07-4a78-a615-ce1f5184aeb1'

    def _get_url_title(self, event):
        """
                               Получение ссылки и названия мероприятия.
                                      Args:
                                          event: (object) принимает объект lxml

                                      Returns:
                                           event_url,  event_title
                               """
        for data in event.xpath("div[@class='box-shadows']/div[contains(@class, 'info')] "
                                "/div[contains(@class, 'col-xs-8')]/div[contains(@class, 'title')]"):
            event_url = data.xpath("div/a/@href")[0]
            event_title = data.xpath("div/a")[0].text
        return event_url, event_title


    def _get_date_time(self, event):
        """
                               Получение даты и врмени мероприятия в формате datetime.
                                      Args:
                                          event: (object) принимает объект lxml

                                      Returns:
                                           дата мероприятия
                               """
        now = datetime.now()
        for item in event.xpath("div"):
            event_day_str = " ".join(item.xpath("div/text()")[0].split()).split()[0]
            event_month_str = " ".join(item.xpath("div/text()")[0].split()).split()[1]
            event_time_str = " ".join(item.xpath("div/text()")[1].split())
            try:
                month = RussianLocale.month_abbreviations.index(event_month_str.lower())
            except ValueError:
                month = RussianLocale.month_names.index(event_month_str.lower())

            year = int(now.year)
            if now.month > month:
                year+=1
            event_start_at = datetime.strptime(event_day_str + '.' + str(month) +
                                               '.' + str(year) + ':' + event_time_str, '%d.%m.%Y:%H:%M')
            return event_start_at

    def get_event_data(self, hook):
        """
                        Получение мероприятий.
                               Args:
                                   hook: (str) принимает ссылку площадки

                               Returns:
                                   (list) список мероприятий
                        """
        result = []
        response = requests.get(hook, headers=self.HEADERS)
        if not response.status_code == 200:
            return result
        html = etree.HTML(response.text)
        for event in html.xpath("//div[@class='event col-xs-6']"):
            result.append({
                "event_hook": self.url + self._get_url_title(event)[0],
                "event_name": self._get_url_title(event)[1],
                "event_start_at": self._get_date_time(event)
            })

        return result

    def _get_widget_url_id(self, event_hook):
        r = requests.get(event_hook, headers=self.HEADERS)
        html = etree.HTML(r.text)
        script_data = html.xpath("//script[contains(text(), 'ticketsteam-825')]/text()")[0]
        steam_id = re.findall(r'ticketsteam-825@\d{6}', script_data)[0]
        widget_url = f'https://widget.afisha.yandex.ru/w/sessions/{steam_id}?clientKey={self.client_key}'
        return widget_url, steam_id

    def _get_headers_id(self, widget_url, widget_headers):
        try:
            res = requests.get(widget_url, headers=widget_headers)
            content = etree.HTML(res.text)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [404]:
                return tickets
            if e.response.status_code in [400, 500, 502]:
                return None
            raise e
        except requests.exceptions.ProxyError:
            return None
        script = content.xpath('//script[contains(., "X-Yandex-Uid")]//text()')
        token = re.findall(r'"X-CSRF-Token":"(.+?)"', script[0])[0]
        request_id = re.findall(r'X-Request-Id":"(.+?)"', script[0])[0]
        yandex_uid = re.findall(r'X-Yandex-Uid":"(.+?)"', script[0])[0]
        headers = {
            'Host': 'widget.afisha.yandex.ru',
            'x-csrf-token': token,
            'x-request-id': request_id,
            'x-yandex-uid': yandex_uid,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        return headers

    def _get_sessions(self, sessions_url, sessions_headers):
        try:
            res = requests.get(sessions_url, headers=sessions_headers)
            sessions_content = res.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 502, 534]:
                return None
            raise e
        sessions = sessions_content.get('result', {}).get('session', {}).get('key')
        return sessions

    def _get_seat(seats, seat):
        '''
        :param categories:
        :param category:
        :return:
        '''
        for s in seats:
            if seat == s.get('categoryId'):
                return s
        return {}

    def _fetch_tickets_data(self, tickets_url, sessions_header):
        result = []
        try:
            res = requests.get(tickets_url, headers=sessions_header)
            tickets_content = res.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 502, 534]:
                return None
            raise e
        try:
            sectors = tickets_content.get('result').get('hallplan').get('levels')
        except:
            # проверяем есть ли вообще билеты
            if tickets_content.get('result').get('saleStatus') == 'no-seats':
                return result
                # если билеты все-таки есть пробуем еще раз запросить данные после небольшой паузы
            else:
                # пробуем еще раз запросить данные после небольшой паузы
                time.sleep(5)
                try:
                    res = requests.get(tickets_url, headers=sessions_header)
                    tickets_content = res.json()
                    sectors = tickets_content.get('result').get('hallplan').get('levels')
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [500, 502, 534]:
                        return None
                except AttributeError:
                    logger.error(f'YANDEX_TICKETS: {tickets_content} {widget_url}')
                    return result
                raise e

        for sector in sectors:
            ticket_list = sector.get('seats')
            section_name = sector.get('name')

            if not sector.get('admission'):
                for ticket in ticket_list:
                    seat_id = ticket.get('sourceSeatId')
                    row = ticket.get('seat').get('row')
                    place = ticket.get('seat').get('place')
                    nominal_price = ticket.get('priceInfo', {}).get('price', {}).get('value')

                    if all((section_name, seat_id, row, place, nominal_price)):
                        seat_dict = {
                            'seat_id': seat_id,
                            'sector_name': section_name,
                            'row_name': row,
                            'seat_name': place,
                            'nominal_price': int(float(nominal_price / 100)),
                            'currency': 'rur',
                            'qty_available': 1,
                            'is_multiple': False,
                        }

                        result.append(seat_dict)
            else:
                for category in sector.get('categories'):
                    seat = self._get_seat(seats=sector.get('seats'), seat=category.get('id'))
                    category_id = category.get('id')
                    nominal_price = seat.get('priceInfo', {}).get('price', {}).get('value')
                    qty_available = category.get('availableSeatCount')
                    seat_name = category.get('name')
                    section_name = category.get('name')

                    if all((section_name, seat_name, category_id, qty_available, nominal_price)):
                        seat_dict = {
                            'seat_id': category_id,
                            'sector_name': section_name,
                            'nominal_price': int(float(nominal_price / 100)),
                            'currency': 'rur',
                            'qty_available': qty_available,
                            'is_multiple': True,
                        }
                        result.append(seat_dict)
        return result

    def get_tickets_data(self, event_hook):
        result_dict = {
            'tickets': [],
            'is_stable': True
        }
        widget_headers = {'Host': 'widget.afisha.yandex.ru'}
        widget_url = self._get_widget_url_id(event_hook)[0]
        steam_id = self._get_widget_url_id(event_hook)[1]
        sessions_url = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{steam_id}?clientKey={self.client_key}'
        sessions_headers = self._get_headers_id(widget_url, widget_headers)
        sessions = self._get_sessions(sessions_url, sessions_headers)
        tickets_url = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{sessions}/hallplan/async?clientKey={self.client_key}'
        result = self._fetch_tickets_data(tickets_url, sessions_headers)
        result_dict['tickets'].extend(result)
        return result_dict


















