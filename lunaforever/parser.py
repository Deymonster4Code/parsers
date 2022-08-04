import json
import re
from datetime import datetime

import requests
from lxml import etree


class LunaForeverParser:
    """
    Парсер для площадки https://lunaforever.love/tour.
    """

    PARSER_NAME = "lunaforever.love"
    EVENTS_HOOK_HELP = 'Пример, https://lunaforever.love/tour'
    TICKETS_HOOK_HELP = "Пример, https://luna.tele-club.ru/?buyticket=654ea240-ddf3-11ea-bce0-297c4c2627f7&step=1"

    headers = {
        'Host': 'lunaforever.love',
        'User-Agent': 'Mozilla/5.0(X11;Linuxx86_64;rv: 78.0)Gecko/20100101Firefox / 78.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp, * / *;q = 0.8',
        'Accept-Language': 'ru-RU,ru;q =0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip,deflate,br',
        'Connection': 'keep-alive',
        'Cookie': 'sessID=53002688c609c5b1e1039d4bf51baebb',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    headers_luna = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://luna.tele-club.ru',
        'Connection': 'keep-alive',
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
        response = requests.get(hook, headers=self.headers)
        i = 0
        html = etree.HTML(response.text)
        for item in html.xpath('//div[@class="events__item"]'):
            link = item.xpath('div[3]/div[1]/a/@href')[0]
            link = str(link).strip()
            if 'kassy' in link:
                response = requests.get(link)
                html = etree.HTML(response.text)
                hook = link
                start_our = html.xpath('//p[@class="venue"]/b')[0].text
            elif 'tele' in link:
                try:
                    event_id = self._get_id_for_time(link)[i]
                    hook = 'https://luna.tele-club.ru/?buyticket=' + event_id + '&step=1'
                except IndexError:
                    continue
                data = '{"telekassa_slug": "%s"}' % event_id
                response = requests.post('https://luna.tele-club.ru/data/buyticket', headers=self.headers_luna,
                                         data=data)
                date = response.json()['data']['Event']['date'].split(' ')[1]
                start_our = date
                i += 1
            else:
                continue
            day, month = item.xpath('div[@class="events__date"]')[0].text.split('.')
            day = int(day)
            month = int(month)
            title = item.xpath('div[@class="events__location"]')[0].text
            now = datetime.now()
            current_date = datetime.now()
            year = current_date.year
            if current_date.month > current_date.month > month:
                year += 1
            date_time_object = datetime.strptime(f'{year}{day}.{month}{start_our}', '%Y%d.%m%H:%M')
            if all((title, month, start_our)):
                result.append({
                    "event_hook": hook,
                    "event_name": 'Луна тур | ' + title,
                    "event_starts_at": date_time_object,
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
        response = requests.get('https://luna.tele-club.ru/')
        html = etree.HTML(response.content)
        x_csrf_token = html.xpath('//meta[@name="csrf-token"]')[0].attrib['content']
        self.headers_luna['x-csrf-token'] = x_csrf_token
        token = seance_hook.split('=')[1].split('&')[0]
        data = '{"telekassa_slug": "%s"}' % token
        tickets_content = requests.post(seance_hook, headers=self.headers_luna, data=data, verify=True)
        # При статусе 404 возвращается пустой список билетов с флагом корректного получения
        if response.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif response.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict
        if 'luna' in seance_hook:
            token = seance_hook.split('=')[1].split('&')[0]
            data = '{"telekassa_slug": "%s"}' % token
            response = requests.post('https://luna.tele-club.ru/data/buyticket', headers=self.headers_luna, data=data)
            data = response.json()['data']['pricesByZones']
            zone = ''
            if data.get('tantspol'):
                zone = 'tantspol'
            elif data.get('dance'):
                zone = 'dance'
            seat_id = data[zone]['id']
            sector_name = data[zone]['title']
            nominal_price = int(float(data[zone]['min']))
            qty_available = int(data[zone]['quotaLeft'])
            if all((seat_id, sector_name, nominal_price, qty_available)):
                result.append({
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'nominal_price': nominal_price,
                    'currency': 'rub',
                    'qty_available': qty_available,
                    'is_multiple': True,
                })
            if data.get('vipnoplace', False):
                seat_id = data['vipnoplace']['id']
                sector_name = data['vipnoplace']['title']
                nominal_price = int(float(data['vipnoplace']['min']))
                qty_available = int(data['vipnoplace']['quotaLeft'])
                if all((seat_id, sector_name, nominal_price, qty_available)):
                    result.append({
                        'seat_id': seat_id,
                        'sector_name': sector_name,
                        'nominal_price': nominal_price,
                        'currency': 'rub',
                        'qty_available': qty_available,
                        'is_multiple': True,
                    })
            data = '{"event_id": "%s"}' % token
            response = requests.post('https://luna.tele-club.ru/data/scheme_data', headers=self.headers_luna, data=data)
            if response.status_code == 200:
                data = response.json()['data']
                for item in data['places']:
                    seat_id = item['top']
                    sector_name = self._change_name(item['id'].split('-')[0])
                    row_name = item['id'].split('-')[1]
                    seat_name = item['id'].split('-')[2]
                    nominal_price = int(float(item['cost']))
                    if all((seat_id, sector_name, nominal_price, row_name, seat_name)):
                        result.append({
                            'seat_id': seat_id,
                            'sector_name': sector_name,
                            'row_name': row_name,
                            'seat_name': '№' + seat_name,
                            'nominal_price': nominal_price,
                            'currency': 'rub',
                            'qty_available': 1,
                            'is_multiple': False,
                        })
        if 'kassy' in seance_hook:
            # TODO Привести в кареольный вид
            # kassy_get_tickets_data(seance_hook)
            pass
        result_dict['tickets'] = result
        return result_dict

    def _change_name(self, title):
        """Получение название места.

        Args:
            title: (str) принимает название на английском языке

        Returns:
            (str)
        """
        if 'table' in title:
            title = 'tables'
        places = {
            'right': 'Правый балкон',
            'center': 'Центральный балкон',
            'tables': 'Стол',
            'left': 'Левый балкон',
            'balkon': 'Балкон'
        }
        return places[title]

    def _get_id_for_time(self, hook):
        """Получение id событий.

        Args:
            hook: (str) принимает ссылку

        Returns:
            (list)
        """
        response = requests.get(hook)
        html = etree.HTML(response.content)
        script = html.xpath('//script')[9].text
        data = json.loads(re.search(r"Data\.Page\s=(.*);Data\.Event", script)[1])
        events = data['sections'][2]['data']['events']
        events_id = [i['tickets_data']['event_id'] for i in events if i['tickets_data']]
        return events_id
