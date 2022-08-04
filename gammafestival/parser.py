import time
from datetime import datetime

import requests
from lxml import etree


class GammaFestivalParser:
    """
    Парсер для площадки https://gammafestival.ru/.
    """

    PARSER_NAME = "gammafestival.ru"
    EVENTS_HOOK_HELP = 'Пример, https://gammafestival.ru/'
    TICKETS_HOOK_HELP = "Пример, https://gammafestival.ru/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-type': 'application/json',
        'Authorization': '',
        'Origin': 'https://ticketscloud.com',
        'TE': 'Trailers',
    }

    data = '{"event": "%s"}'

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        self._get_token(hook)
        data = self.data % self._get_event_token(hook)
        data = requests.post('https://ticketscloud.com/v1/services/widget', headers=self.headers, data=data).json()
        title = data['event']['title']['text']
        date_time_object_start = datetime.strptime(data['event']['lifetime']['start'].split("+")[0],
                                                   '%Y-%m-%dT%H:%M:%S')
        date_time_object_end = datetime.strptime(data['event']['lifetime']['finish'].split("+")[0], '%Y-%m-%dT%H:%M:%S')
        if all((title, date_time_object_start, date_time_object_end)):
            result.append({
                "event_hook": hook,
                "event_name": title,
                "event_starts_at": date_time_object_start,
                "event_end_at": date_time_object_end,
            })
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
        self._get_token(seance_hook)
        data = self.data % self._get_event_token(seance_hook)
        response = requests.post('https://ticketscloud.com/v1/services/widget', headers=self.headers, data=data)
        data = response.json()
        for item in data['sets']:
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            a = item
            if data['sets'][a]['amount_vacant'] == 0:
                continue
            result.append({
                'seat_id': data['sets'][a]['id'],
                'sector_name': 'Входной билет',
                'nominal_price': int(float(data['sets'][a]['prices'][0]['nominal'])),
                'currency': 'rub',
                'qty_available': data['sets'][a]['amount_vacant'],
                'is_multiple': True,

            })
        result_dict['tickets'] = result
        return result_dict

    def _get_token(self, hook):
        """Получение токена для  headers.

        Args:
            hook: (str) принимает ссылку площадки
        """
        response = requests.get(hook)
        html = etree.HTML(response.text)
        result = html.xpath('//a[@class="t-btn t-btn_sm "]/@href')[0].split("&")[1].split('=')[1]
        self.headers['Authorization'] = 'token ' + result

    def _get_event_token(self, hook):
        """Получение токена для  data.

        Args:
            hook: (str) принимает ссылку площадки
        Returns:
            (str)
        """
        response = requests.get(hook)
        html = etree.HTML(response.text)
        result = html.xpath('//a[@class="t-btn t-btn_sm "]/@href')[0].split('=')[1].split('&')[0]
        return result
