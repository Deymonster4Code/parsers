import base64
import json
from datetime import datetime

import requests
from arrow.locales import RussianLocale
from lxml import etree


class CircusSaratovParser:
    """
    Парсер для площадки https://www.circus-saratov.ru/.

    """
    PARSER_NAME = "circus-saratov.ru"
    EVENTS_HOOK_HELP = 'Пример, https://www.circus-saratov.ru/'
    TICKETS_HOOK_HELP = "Пример, https://widget2.kassy.ru/auth/circus.ru/?back=/saratov/event/4446/"

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку на главную страницу площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        response = requests.get(hook, verify=False)
        events = etree.HTML(response.text)
        for event in events.xpath('//div[@class="row"]/div/div/div/div/div/div[@class="ticket_item text-center"]'):
            day = event.xpath('p')[0].text
            month = RussianLocale.month_abbreviations.index(event.xpath('p')[1].text[:3].lower())
            current_date = datetime.now()
            year = current_date.year
            if current_date.month > month:
                year += 1
            for circus_sessions in event.xpath('a'):
                hour = circus_sessions.xpath('p')[0].text
                if 'Продано' in hour:
                    continue
                title = 'Цирк Саратов ({0}.{1}.{2} {3})'.format(day, month, year, hour.split(' ')[2])
                event_id = str(circus_sessions.xpath('@data-kassy-event_id')[0])
                event_hook = 'https://widget2.kassy.ru/auth/circus.ru/?back=/saratov/event/{0}/'.format(event_id)
                date_time_object_start = datetime.strptime(str(year) + str(month) + day + hour.split(' ')[2],
                                                           '%Y%m%d%H:%M')
                result.append({
                    "event_hook": event_hook,
                    "event_name": title,
                    "event_starts_at": date_time_object_start,
                })
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов c конкретного мероприятия.

        Args:
            seance_hook: (str) принимает ссылку определенного мероприятия

        Returns:
            (dict)
        """
        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        response = requests.get(seance_hook)
        event_id = seance_hook.split('/')[8]
        session_id = response.url.split('session_id=')[1]
        result = self._kassy_get_tickets_data(event_id, session_id)
        result_dict['tickets'] = result
        return result_dict

    def _kassy_get_tickets_data(self, event_id, session_id):
        cookies = {
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }

        params = (
            ('ts_id', '2'),
            ('event_id', event_id),
            ('version', 'dd'),
            ('session_id', session_id),
        )
        tickets = []

        content_str = requests.get('https://widget2.kassy.ru/api/hall/', headers=headers, params=params,
                                   cookies=cookies)
        content_str = base64.b64decode(content_str.text)
        content_json = json.loads(content_str)

        for section in content_json.get('sections', []):
            sector_name = section.get('section_title')
            for seat in section.get('places'):
                status = seat.get('state')
                if status == 1:
                    seat_id = seat.get('place_id')
                    row_name = seat.get('row')
                    seat_name = seat.get('seat')
                    nominal_price = seat.get('price')

                    if row_name == '-':
                        row_name = '1'

                    if seat.get('row_metric') == 'Стол':
                        if 'стол' not in sector_name:
                            sector_name_full = f'{sector_name} стол {row_name}'
                        else:
                            sector_name_full = f'{sector_name} {row_name}'
                        row_name = '1'
                    else:
                        sector_name_full = sector_name

                    if all((seat_id, row_name, seat_name, nominal_price)):
                        seat_dict = {
                            'seat_id': seat_id,
                            'sector_name': sector_name_full,
                            'row_name': row_name,
                            'seat_name': seat_name,
                            'nominal_price': nominal_price,
                            'currency': 'rur',
                            'qty_available': 1,
                            'is_multiple': False,
                        }
                        tickets.append(seat_dict)
                        # print(seat_dict)
        return tickets
