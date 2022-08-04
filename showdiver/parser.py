import re
import time
from datetime import datetime

import requests


# class ShowdiverEvent(GenericParser):
class ShowdiverEvent:
    """
    Парсер для площадки https://showdiver.com/.
    """

    PARSER_NAME = "showdiver.com"
    EVENTS_HOOK_HELP = 'Пример, https://showdiver.com/'
    TICKETS_HOOK_HELP = "Пример, https://showdiver.com/events/4fc1ffa0-60b9-40b4-9229-1c55a910b980"

    HEADERS = {'authority': ''}

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        data = self._get_event(hook)
        for uuid in data:
            url = 'https://api.showdiver.com/events/' + uuid
            response = requests.get(url)
            data = response.json()
            date_time_obj = datetime.strptime(data['start_at'], '%Y-%m-%dT%H:%M:%SZ')
            if all((data['title'], date_time_obj, data['venue']['title'])):
                result.append({
                    "event_hook": 'https://showdiver.com/events/' + uuid,
                    "event_name": data['title'],
                    "event_starts_at": date_time_obj,
                    "hall_name": data['venue']['title'],
                })
                time.sleep(1)
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов c конкретного мероприятия.

        Args:
            seance_hook: (str) принимает ссылку определенного мероприятия

        Returns:
            (dict)
        """
        result = []
        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        uuid = seance_hook.split('/')[-1]
        url = 'https://api.showdiver.com/events/' + uuid
        response = requests.get(url)
        data = response.json()['price_categories']
        for item in data:
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            if not data:
                continue
            if 'место' in item['title']:
                if all((item['uuid'], item['title'])):
                    result.append({
                        'seat_id': item['uuid'],
                        'sector_name': item['title'],
                        'row_name': self._chek_row(item['title']),
                        'seat_name': re.search(r"место\s*№*(.*)", item['title'])[1],
                        'nominal_price': int(float(item['price'])),
                        'currency': 'rub',
                        'qty_available': 1,
                        'is_multiple': False,
                    })
                    time.sleep(1)
            else:
                result.append({
                    'seat_id': item['uuid'],
                    'sector_name': item['title'],
                    'nominal_price': int(float(item['price'])),
                    'currency': 'rub',
                    'qty_available': 2,
                    'is_multiple': True,

                })
                time.sleep(1)
            result_dict['tickets'] = result
        return result_dict

    def _get_event(self, hook):
        """Получение uuid с сайта.

        Args:
            hook: (str) принимает ссылку площадки (https://showdiver.com/)

        Returns:
            (list)
        """
        if hook == 'https://showdiver.com/':
            page = 1
            num = 1
            result = []
            while num < 2:
                url = 'https://api.showdiver.com/events/?page=' + str(
                    page) + '&page_size=16&search=&period_start=&period_end='
                page += 1
                response = requests.get(url)
                if response.json().get('detail') == "Неправильная страница":
                    break
                data = response.json()['results']
                for item in data:
                    uuid = item['uuid']
                    result.append(uuid)
                    time.sleep(1)
            return result

    def _chek_row(self, text):
        """Получение ряда если есть.

        Args:
            text: (str) принимает текст

        Returns:
            (int)
        """
        if 'ряд' in text:
            a = re.search(r"ряд\s*(.*),", text)[1]
            return int(a)
        else:
            return 1
