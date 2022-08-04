import datetime
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from arrow.locales import RussianLocale
from lxml import etree


class Bileter:
    """
    Парсер для площадки https: //www.bileter.ru/
    """

    PARSER_NAME = "bileter.ru"
    EVENTS_HOOK_HELP = 'Пример, https://www.bileter.ru/afisha'
    TICKETS_HOOK_HELP = "Пример, https://www.bileter.ru/performance/18148169"
    base_url = 'https://www.bileter.ru'
    afisha_url = 'https://www.bileter.ru/afisha'
    url_hooks = []
    result = []

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'

    }

    def _get_event_from_url(self, url, timeout=10):
        events_url = []
        time.sleep(1)
        response = requests.get(url, timeout=timeout, headers=self.HEADERS)
        html = etree.HTML(response.text)
        for event in html.xpath('//div[@class="afishe-item"]'):
            event_title = event.xpath('div[@class="info-block"]/div[@class="name"]/a/@title')[0]

            # проверка событий на количество дат
            try:
                event_hook = self.base_url + event.xpath('div[@class="info-block"]/div[@class="price"]/a/@href')[0]
                event_date_time_ctr = event.xpath('div[@class="info-block"]/div[@class="date"]/text()')[0]
                if event_date_time_ctr == 'Открытая дата':
                    continue
                """проверка на неправильные записи - когда несколько дат, но списка выпадающего нет
                делаем отдельный запрос на страницу чтобы получить все даты из выпадающего списка"""
                if "-" in event_date_time_ctr:
                    res = requests.get(event_hook, headers=self.HEADERS)
                    html1 = etree.HTML(res.text)
                    for dates in html1.xpath('//ul[@class="drop-day-list"]/li'):
                        event_hook1 = self.base_url + dates.xpath('a/@href')[0]
                        event_date_time = self._get_one_date_time(dates.xpath('a/text()')[0])
                        if all((event_hook1, event_title, event_date_time)):
                            events_url.append({
                                "event_hook": event_hook1,
                                "event_name": event_title,
                                "event_starts_at": event_date_time
                            })

                # событие с одной датой
                else:
                    event_date_time = self._get_one_date_time(event_date_time_ctr)
                    if all((event_hook, event_title, event_date_time)):
                        events_url.append({
                            "event_hook": event_hook,
                            "event_name": event_title,
                            "event_starts_at": event_date_time
                        })
            # события с несколькими датами, несколькими хуками и выпадающим списком
            except IndexError:
                for date in event.xpath(
                        'div[@class="info-block"]/div[@class="price"]/div/ul[contains(@class, "dropdown-menu")]/li'):
                    event_hook = self.base_url + date.xpath('a/@href')[0]
                    event_date_time = self._get_one_date_time(date.xpath('a/text()')[0])

                    if all((event_hook, event_title, event_date_time)):
                        events_url.append({
                            "event_hook": event_hook,
                            "event_name": event_title,
                            "event_starts_at": event_date_time
                        })

        return events_url

    @staticmethod
    def _get_one_date_time(date_ctr):
        """
        :param date_ctr - необработанная строка с датой:
        :return datetime format дата:
        """
        #if date_ctr == 'Открытая дата':
        #    return
        now = datetime.now()
        raw_date = date_ctr.strip().replace(",", "").split(" ")
        if len(raw_date[2]) == 4 and ":" not in raw_date[2]:
            event_time_str = raw_date[3]
            event_day_str = raw_date[0]
            month_str = raw_date[1]
            year = raw_date[2]
            month = RussianLocale.month_names.index(month_str.lower())
        else:
            event_time_str = raw_date[2]
            event_day_str = raw_date[0]
            month_str = raw_date[1]
            year = int(now.year)
            month = RussianLocale.month_names.index(month_str.lower())
            if now.month > month:
                year += 1
        try:
            event_starts_at = datetime.strptime(event_day_str + '.' + str(month) + '.' + str(year) + ':' + event_time_str,
                                            '%d.%m.%Y:%H:%M')
            return event_starts_at
        except ValueError:
            print("Ошибка в формате записи даты")
            return

    @staticmethod
    def _end(html):
        if html.xpath('//li[@class="next disabled"]'):
            return True
        else:
            return False

    @staticmethod
    def _exist(html):
        if html.xpath('//div[@class="afishe-preview type-3"]/p'):
            return False
        else:
            return True


    def _search_end(self, max=500):
        # алгоритм поиска количества страниц: в выбранном диапазоне от min до max.
        # делим диапазон на пополам - проверяем страницу из середины
        # сначала проверка на существование вообще событий - def exist()
        # если событий нет, то делим еще раз пополам - шан влево
        # если есть то проверяем последняя ли это страница, если да то выдаем ее номер
        # если не последняя то делаем шаг вправо
        min = 0
        max = 1000
        mid = int((max - min) / 2)
        while True:
            res = requests.get(f'{self.afisha_url}?page={mid}', headers=self.HEADERS)
            html = etree.HTML(res.text)
            if not self._exist(html):
                max = mid
                mid = int(mid / 2)
                continue
            else:
                if not self._end(html):
                    mid = int((max - mid) / 2 + mid)
                    continue
                else:
                    break
        return mid

    def _get_all_event_data(self):
        result = []
        end_page = self._search_end(500)
        urls = [f'{self.afisha_url}?page={i}' for i in range(1, end_page+1)]
        with ThreadPoolExecutor() as executor:
            url_evens = executor.map(self._get_event_from_url, urls)
        for events in url_evens:
            for event in events:
                result.append(event)
        return result

    def get_event_data(self, hook):
        result = []
        response = requests.get(hook, headers=self.HEADERS)
        html = etree.HTML(response.text)
        for event in html.xpath('//div[contains(@class, "afishe-item")]'):
            event_title = event.xpath('div[@class="info-block"]/div[@class="name"]/a/@title')[0]

            # проверка событий на количество дат
            try:
                event_hook = self.base_url + event.xpath('div[@class="info-block"]/div[@class="price"]/a/@href')[0]
                event_date_time_ctr = event.xpath('div[@class="info-block"]/div[@class="date"]/text()')[0]
                if event_date_time_ctr == 'Открытая дата':
                    continue
                """проверка на неправильные записи - когда несколько дат, но списка выпадающего нет
                делаем отдельный запрос на страницу чтобы получить все даты из выпадающего списка"""
                if "-" in event_date_time_ctr:
                    res = requests.get(event_hook, headers=self.HEADERS)
                    html1 = etree.HTML(res.text)
                    for dates in html1.xpath('//ul[@class="drop-day-list"]/li'):
                        event_hook1 = self.base_url + dates.xpath('a/@href')[0]
                        event_date_time = self._get_one_date_time(dates.xpath('a/text()')[0])
                        if all((event_hook1, event_title, event_date_time)):
                            result.append({
                                "event_hook": event_hook1,
                                "event_name": event_title,
                                "event_starts_at": event_date_time
                            })

                # событие с одной датой
                else:
                    event_date_time = self._get_one_date_time(event_date_time_ctr)
                    if all((event_hook, event_title, event_date_time)):
                        result.append({
                            "event_hook": event_hook,
                            "event_name": event_title,
                            "event_starts_at": event_date_time
                        })
            # события с несколькими датами, несколькими хуками и выпадающим списком
            except IndexError:
                for date in event.xpath(
                        'div[@class="info-block"]/div[@class="price"]/div/ul[contains(@class, "dropdown-menu")]/li'):
                    event_hook = self.base_url + date.xpath('a/@href')[0]
                    event_date_time = self._get_one_date_time(date.xpath('a/text()')[0])

                    if all((event_hook, event_title, event_date_time)):
                        result.append({
                            "event_hook": event_hook,
                            "event_name": event_title,
                            "event_starts_at": event_date_time
                        })

        return result



    def _fetch_tickets_data(self, json_data):
        result = []
        if not json_data.get('activePlaces'):
            return result
        else:
            if not json_data.get('texts'):
                for ticket in json_data.get('activePlaces'):
                    seat_id = ticket['id']
                    section_name = ticket['description']
                    nominal_price = int(ticket['price'])
                    if all((seat_id, section_name, nominal_price)):
                        seat_dict = {
                            'seat_id': seat_id,
                            'sector_name': section_name,
                            'nominal_price': nominal_price,
                            'currency': 'rur',
                            'qty_available': 1,
                            'is_multiple': True
                        }
                        result.append(seat_dict)
            else:
                for ticket in json_data.get('activePlaces'):
                    seat_id = ticket['id']
                    section_name = ticket['section']
                    row = ticket['row']
                    place = ticket['place']
                    nominal_price = int(ticket['price'])
                    if all((seat_id, section_name, row, place, nominal_price)):
                        seat_dict = {
                            'seat_id': seat_id,
                            'sector_name': section_name,
                            'row_name': row,
                            'seat_name': place,
                            'nominal_price': nominal_price,
                            'currency': 'rur',
                            'qty_available': 1,
                            'is_multiple': False
                        }
                        result.append(seat_dict)
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        result_dict = {
            'tickets': [],
            'is_stable': True
        }
        url_hall = f'https://www.bileter.ru/performance/hall-scheme?IdPerformance={seance_hook.split("/")[-1]}'
        try:
            res = requests.get(url_hall)
            halldata = res.text.split('\\n')[5].strip().split('=')[1][:-1].encode().decode('unicode_escape')
            json_data = json.loads(halldata)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 502, 534]:
                return None
            raise e
        result = self._fetch_tickets_data(json_data)
        result_dict['tickets'].extend(result)
        return result_dict


#event_hook = 'https://www.bileter.ru/performance/18331318'
events = Bileter()
hook = 'https://www.bileter.ru/afisha/building/dk_vyiborgskiy.html'
print(len(events.get_event_data(hook)))
#print(events.get_tickets_data(event_hook))









