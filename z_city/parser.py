import hashlib
from datetime import datetime

import requests
from lxml import etree


class ZCityParser:
    """
    Парсер для площадки https://z.city.
    """

    PARSER_NAME = "z.city"
    EVENTS_HOOK_HELP = 'Пример, https://z.city/#rec267774265'
    TICKETS_HOOK_HELP = "Пример, https://pay.z.city/?event=zboat"

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        response = requests.get(hook)
        html = etree.HTML(response.text)
        for item in html.xpath('//span[@style="font-size: 26px;"]/strong'):
            data = {
                "event_hook": '',
                "event_name": '',
                "event_starts_at": '',
            }
            title = item.text.split(' ')[0]
            now = datetime.now()
            month = item.text.split(' ')[1].split('.')[1]
            current_date = datetime.now()
            year = str(now.year)
            if current_date.month > current_date.month > month:
                year += 1
            day = item.text.split(' ')[1].split('.')[0]
            date_time_obj = datetime.strptime(year + '-' + month + '-' + day + '10:00', '%Y-%m-%d%H:%M')
            if all((title, month, day)):
                if title == 'Z.BOAT':
                    hook = html.xpath('//div[@style="margin-top:60px;"]/a')[1].attrib['href']
                elif title == 'Z.FEST':
                    hook = 'https://z.city/' + html.xpath('//div[@style="margin-top:60px;"]/a')[0].attrib['href']
                data['event_hook'] = hook
                data['event_name'] = title
                data['event_starts_at'] = date_time_obj
            try:
                if item.text.split('-')[1]:
                    a = item.text.split('-')[1]
                    month = a.split('.')[1]
                    day = a.split('.')[0]
                    event_end_at = datetime.strptime(year + '-' + month + '-' + day + '23:00', '%Y-%m- %d%H:%M')
                    if all((month, day)):
                        data['event_end_at'] = event_end_at
            except IndexError:
                result.append(data)
                continue
            result.append(data)
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
        response = requests.get(seance_hook)
        if response.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif response.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict
        if 'https://z.city' in seance_hook:
            html = etree.HTML(response.text)
            for item in html.xpath('//div[@class="t778__content"]'):
                prise = item.xpath('a/div/div[3]/div/div[1]')[0].text.split(' ')[0] + \
                        item.xpath('a/div/div[3]/div/div[1]')[0].text.split(' ')[1]
                hash_object = hashlib.md5(item.xpath('a/div/div/div')[0].text.encode())
                sector_name = item.xpath('a/div/div/div')[0].text
                if all((prise, sector_name, hash_object)):
                    result.append({
                        'seat_id': hash_object.hexdigest(),
                        'sector_name': sector_name,
                        'nominal_price': int(float(prise)),
                        'currency': 'rub',
                        'qty_available': 1,
                        'is_multiple': True,
                    })
                result_dict['tickets'] = result
            return result_dict
        if 'https://pay.z.city/' in seance_hook:
            response = requests.get(seance_hook)
            html = etree.HTML(response.text)
            for item in html.xpath('//div[@class="tickets_dtype"]'):
                hash_object = hashlib.md5(item.xpath('div[@class="ticket_name"]')[0].text.encode())
                sector_name = item.xpath('div[@class="ticket_name"]')[0].text
                price = int(float(item.xpath('div[@class="ticket_price"]/p')[0].text))
                if all((hash_object, sector_name, price)):
                    result.append({
                        'seat_id': hash_object.hexdigest(),
                        'sector_name': sector_name,
                        'nominal_price': price,
                        'currency': 'rub',
                        'qty_available': 9,
                        'is_multiple': True,
                    })
                result_dict['tickets'] = result
            return result_dict
