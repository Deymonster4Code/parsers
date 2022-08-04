import re
import time
from datetime import datetime

import requests


# class AfishaEvent(GenericParser):
class AfishaEvent:
    """
    Парсер для площадки https://afisha.timepad.ru/.
    """

    PARSER_NAME = "afisha.timepad.ru"
    EVENTS_HOOK_HELP = 'Пример, https://afisha.timepad.ru/organizations/24253/events'
    TICKETS_HOOK_HELP = "Пример, https://afisha.timepad.ru/event/1642755"

    HEADERS = {'authority': 'ontp.timepad.ru'}

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        data = self._get_event(hook)
        result = []
        for item in data:
            date_time_obj = datetime.strptime(item['startDate'], '%Y-%m-%d %H:%M:%S')
            if all(('https://afisha.timepad.ru/event/' + item['id'], item['title'], date_time_obj)):
                result.append({
                    "event_hook": 'https://afisha.timepad.ru/event/' + item['id'],
                    "event_name": item['title'],
                    "event_starts_at": date_time_obj,
                })
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов.

        Args:
            seance_hook: (str) принимает ссылку определенного мероприятия

        Returns:
            (dict)
        """
        base_url = seance_hook.split('/')[-1]
        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        result = []
        ticket_url = 'https://ontp.timepad.ru/api/events/'+base_url+'/tickets'
        response_ticket = requests.get(ticket_url)
        ticket_data = response_ticket.json()['tickets']
        for price in ticket_data:
            if not response_ticket.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            if not ticket_data:
                continue
            if all((price['id'], self._get_sector_name(base_url), int(price['maxOrder']))):
                result.append({
                    'seat_id': price['id'],
                    'sector_name': self._get_sector_name(base_url),
                    'nominal_price': int(float(price['price'])),
                    'currency': price['currency'].lower(),
                    'qty_available': int(price['maxOrder']),
                    'is_multiple': True,

                })
        time.sleep(1)
        result_dict['tickets'] = result
        return result_dict

    def _get_event(self, hook):
        """Получение мероприятий с платформы.

        Args:
            hook: (str) принимает ссылку площадки (https://afisha.timepad.ru/organizations/24253/events)

        Returns:
            (dict)
        """
        base_url = hook.split('/')[-2]
        url = 'https://ontp.timepad.ru/api/events/organization?organizationId='+str(base_url)
        response = requests.get(url)
        data = response.json()['list']
        return data

    def _get_sector_name(self, event_id):
        """ Парсит название сектора с поля 'body'.

        Args:
            event_id: (int) принимает id мероприятия

        Returns:
            (str) название сектора
        """
        ticket_url = 'https://ontp.timepad.ru/api/events/' + event_id
        response_ticket = requests.get(ticket_url)
        ticket_data = response_ticket.json()
        a = ticket_data['body']
        re_result = re.search(r"Где:\s*</strong>(.*)<|<p>Где:\s(.*)<|Где</strong>:(.*)<|Где: (.*)</p>", a)
        if not re_result:
            return ''
        sector_name = re_result[1] or re_result[2] or re_result[3] or re_result[4] or re_result[5]
        return sector_name.replace('\xa0', ' ')
