import datetime
from datetime import datetime
import time
import json
import requests
from arrow.locales import RussianLocale
from lxml import etree
import html

class FescoHall:
    """
        Парсер для площадки https: //www.fesco-hall.ru/
        """

    PARSER_NAME = "fesco-hall.ru"
    EVENTS_HOOK_HELP = 'Пример, https://fesco-hall.ru'
    TICKETS_HOOK_HELP = "Пример, https://fesco-hall.ru/event/sergey-orlov-28-01-2022-05-48"
    BASE_URL = 'https://fesco-hall.ru'

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'

    }

    def get_event_data(self, hook):
        """Получение мероприятий.

                Args:
                    hook: (str) принимает ссылку площадки

                Returns:
                    (dict) список мероприятий
                """
        result = []
        response = requests.get(hook, headers=self.HEADERS)
        html = etree.HTML(response.text)
        for event in html.xpath('//article[contains(@class, "small-3")]'):
            event_hook = self.BASE_URL + event.xpath('a/@href')[0]
            try:
                data = event.xpath('footer/div/button/@data-event')[0]
                event_data = json.loads(data)
                event_time_str = event_data['date'].split(' ')[1]
                event_day_str = event_data['date'].split(' ')[0].split('-')[2]
                event_month_str = event_data['date'].split(' ')[0].split('-')[1]
                event_year_str = event_data['date'].split(' ')[0].split('-')[0]
                event_starts_at = datetime.strptime(event_day_str + '.' + event_month_str + '.' + event_year_str + ':' + event_time_str,
                                            '%d.%m.%Y:%H:%M:%S')
                event_title = event_data['title']
                if all((event_hook, event_title, event_starts_at)):
                    result.append({
                        "event_hook": event_hook,
                        "event_name": event_title,
                        "event_starts_at": event_starts_at,
                    })

            except IndexError:
                continue
        return result
    def _get_price(self, price_group_id, tickets_data):
        for price in tickets_data['price_groups']:
            if price_group_id == price['id']:
                return price['price']



    def _fetch_tickets(self, event_id):
        result = []
        tickets_url = f'https://fesco-hall.ru/api/concerts/schema?ticket_system_concert_id={event_id}'
        try:
            res = requests.get(tickets_url, headers=self.HEADERS)
            tickets_data = json.loads(res.text)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 502, 534]:
                return None
            raise e
        for place in tickets_data['places']:
            if not place['sellable']:
                continue
            seat_id = place['id']
            sector_name = place['sector']
            row = place['row']
            seat = place['seat']
            price = self._get_price(place['price_group_id'], tickets_data)
            if all((seat_id, row, sector_name, seat, price)):
                seat_dict = {
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'row_name': row,
                    'seat_name': seat,
                    'nominal_price': price,
                    'currency': 'rur',
                    'qty_available': 1,
                    'is_multiple': False,
                }
                result.append(seat_dict)
        return result

    def get_tickets_data(self, event_hook):
        """Получение билетов c конкретного мероприятия.

               Args:
                   event_hook: (str) принимает ссылку определенного мероприятия

               Returns:
                   (dict)
               """
        result_dict = {
            'tickets': [],
            'is_stable': True
        }
        res = requests.get(event_hook, headers=self.HEADERS)

        html = etree.HTML(res.text)
        event_id = json.loads(html.xpath('//div[@id="buyTicketsModal"]/@data-event')[0])['ticket_system_concert_id']
        result = self._fetch_tickets(event_id)
        result_dict['tickets'].extend(result)
        return result_dict



#events = FescoHall()
#url = 'https://fesco-hall.ru'
#event_hook = 'https://fesco-hall.ru/event/metallica-show-s-m-tribute-23-04-2021-03-32'
#print(events.get_event_data(url))
#print(events.get_tickets_data(event_hook))