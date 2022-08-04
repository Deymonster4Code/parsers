import requests
from lxml import etree
from datetime import datetime
from arrow.locales import RussianLocale


class TnaTickets:
    """
        Парсер для площадки https://tna-tickets.ru/
        """

    PARSER_NAME = "tna-tickets"
    EVENTS_HOOK_HELP = 'Пример, https://tna-tickets.ru/event'
    TICKETS_HOOK_HELP = "Пример, https://tna-tickets.ru/event"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'host': 'tna-tickets.ru'
    }

    url = 'https://tna-tickets.ru/event'
    base_url = 'https://tna-tickets.ru'
    url_seats = 'https://tna-tickets.ru/tickets/api/seats?calendar_id='
    url_price_list = 'https://tna-tickets.ru/tickets/api/seat_price_list?calendar_id='
    url_sectors = 'https://tna-tickets.ru/tickets/api/sectors?calendar_id='

    DATA = []

    # получаем ссылку и название мероприятия
    def _get_url_title(self, concert):
        for a in concert.xpath("div/h3"):
            event_url = a.xpath("a/@href")[0]
            event_title = a.xpath("a")[0].text
            return event_url, event_title

    def _get_event_id(self, concert):
        for a in concert.xpath("div[2]"):
            event_booking = a.xpath("a/@href")[0]
            event_id = event_booking.split('=')[1]
            return event_id

    def _get_sectors_id(self, event_id):

        HEADERS = {
            'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
            'Accept': 'text/plain, */*; q=0.01',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'host': 'tna-tickets.ru'
        }
        result = []
        r = requests.get(f"{self.url_sectors}{event_id}")
        sectors = r.json()
        if sectors['count'] == 0:
            return
        for sector in sectors['body']:
            result.append({
                    'sector_id': sector['sector_id'],
                    'sector_name': sector['name']
                })
        return result


    def _get_date_time(self, concert):
        """
                        Получение даты и врмени мероприятия в формате datetime.
                               Args:
                                   concert: (object) принимает объект lxml

                               Returns:
                                    дата мероприятия
                        """

        now = datetime.now()
        for a in concert.xpath("div/div/b"):
            event_day_str = a.text.split(' ')[0]
            event_month_str = a.text.split(' ')[1]
            event_time_str = a.xpath("following-sibling::text()")[0].replace('/', '').strip(' ')
            month = RussianLocale.month_names.index(event_month_str.lower())
            year = int(now.year)
            if now.month > month:
                year += 1
            event_starts_at = datetime.strptime(event_day_str + '.' + str(month) + '.' + str(year) + ':' + event_time_str, '%d.%m.%Y:%H:%M')
            return event_starts_at

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
        for concert in html.xpath("//div[@class='home_events_item']"):
            if all((self._get_url_title(concert), self._get_date_time(concert))):

                result.append({
                    "event_hook": self.base_url + self._get_url_title(concert)[0],
                    "event_name": self._get_url_title(concert)[1],
                    "event_start_at": self._get_date_time(concert),
                 })
        return result

    def _get_price(self, prices, zone_id):
        for price in prices['body']:
            if price['zone_id'] == zone_id:
                return price['price']

    def _get_row_name(self, seat_name):
        sector_name_list = seat_name.split(' ')
        for word in sector_name_list:
            if word == 'Ряд':
                index = sector_name_list.index(word)
                row_name = ' '.join(sector_name_list[index:index+2])
                return row_name

    def _fetch_tickets_data(self, event_id, sectors_id):
        """
                Получение данных c конкретного мероприятия - id, конкретного сектора - id
                       Args:
                           event_id: (str) принимает id определенного события
                           sectors_id: (dict) принимает список секторов

                       Returns:
                           (dict)
                """

        result = []
        for sector in sectors_id:
            sector_id = sector['sector_id']
            r = requests.get(f"{self.url_seats}{event_id}&sector_id={sector_id}")
            seats = r.json()
            sector_name = sector['sector_name']
            res = requests.get(f"{self.url_price_list}{event_id}")
            prices = res.json()
            if seats['count'] == 0:
                return
            for seat in seats['body']:
                seat_id = seat['seat_id']
                seat_name = seat['name']
                row_name = self._get_row_name(seat_name)
                zone_id = seat['zone_id']
                price = self._get_price(prices, zone_id)
                if all((sector_name, seat_id, seat_name, price)):
                    seat_dict = {
                        'seat_id': seat_id,
                        'sector_name': sector_name,
                        'row_name': row_name,
                        'seat_name': seat_name,
                        'nominal_price': price,
                        'currency': 'rur',
                        'qty_available': 1,
                        'is_multiple': False,
                    }
                    result.append(seat_dict)
        return result



    def get_tickets_data(self, event_hook):

        """
                Получение билетов c конкретного мероприятия.
                       Args:
                           seance_hook: (str) принимает хук определенного события

                       Returns:
                           (dict)
                """

        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        response = requests.get(event_hook, headers=self.HEADERS)
        if not response.status_code == 200:
            return result_dict
        html = etree.HTML(response.text)
        event_id = html.xpath("//div[@class='event-detail__links']/a/@href")[0].split('=')[1]
        sectors_id = self._get_sectors_id(event_id)
        result = self._fetch_tickets_data(event_id, sectors_id)
        result_dict['tickets'].extend(result)
        return result_dict


