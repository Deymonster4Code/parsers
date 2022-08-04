import datetime
import hashlib
import json
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from lxml import etree


class MoscowQTicketsParser:
    """
    Парсер для площадки https://moscow.qtickets.events/.
    """

    PARSER_NAME = "moscow.qtickets.events"
    EVENTS_HOOK_HELP = 'Пример, https://moscow.qtickets.events/'
    TICKETS_HOOK_HELP = "Пример, https://moscow.qtickets.events/25257-vebinar-kak-privlech-investora-v-krizis"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Referer': 'https://moscow.qtickets.events/',
        'TE': 'Trailers',
    }

    TICKETS_HEADERS = {
        'authority': 'www.16tons.ru',
        'method': 'GET',
        'path': '/',
        'scheme': 'https',
    }

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        i = 1
        while 1 > 0:
            print(i)
            params = (
                ('page', str(i)),
            )
            response = requests.get(hook, headers=self.headers, params=params)
            i += 1
            html = etree.HTML(response.text)
            if html.xpath('//div[@class="wrapper"]/h1')[0].tail.strip() == 'Нет ближайших мероприятий':
                break
            for item in html.xpath('//li[@class="item"]'):
                hook = str(item.xpath('section/a/@href')[0])
                title = item.xpath('section/a/h2')[0].text
                date = item.xpath('section/a/time/@datetime')[0].split('+')[0]
                date_time_object = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
                if all((hook, title, date)):
                    result.append({
                        "event_hook": hook,
                        "event_name": title,
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
        result_dict = {
            'tickets': [],
            'is_stable': True,
        }
        tickets = []
        response = requests.get(seance_hook)
        # При статусе 404 возвращается пустой список билетов с флагом корректного получения
        if response.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif response.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict

        if 'moscow' in seance_hook:
            event_id = seance_hook.split('/')[-1].split('-')[0]
            seance_hook = f'https://16tonsarbat.qtickets.ru/event/{event_id}'
            self.TICKETS_HEADERS['authority'] = '16tonsarbat.qtickets.ru'
        else:
            event_id = seance_hook.split('/')[-1]

        hostname = urlparse(seance_hook).hostname
        province_url = f'https://16tons.qtickets.ru/event/{event_id}'
        data = {'event_id': event_id,
                'host': hostname,
                'referer': seance_hook.replace(':', '%3A').replace('?', '%3F').replace('=', '%3D').replace('&',
                                                                                                           '%26').replace(
                    '/', '%2F'),
                'height': '455',
                'iframe': '',
                '__qtickets_session': '94tmZeZMyTqWE9z1auiZaoMuTRwgpO8SpW16baVn',
                'container_width': '1871',
                'handlers': 'resizeHeight|fixIframeSize|loadShow|loadEvent|loadOrganizer|systemComplete|appSlide|setVar|basketTotalSystem|createOrder|resizeDisableAll|resizeEnableAll|InAppBrowser|extendInstanceRequest|complete|error|event|redirectTo|winclose|onSlideShow|onSlideHide|parentLoadInternalScript'
                }
        headers = {'Host': hostname}
        province = requests.post(province_url, headers=headers, data=data)

        src_groups = re.search(r'/storage/temp/bundles/(\d+)/(\d+).ru.js', province.text)
        ordered_tickets = re.search(r'"ordered_seats":(.+),"free_quantity"', province.text)

        if ordered_tickets:
            ordered_seats = json.loads(ordered_tickets.groups()[0])
        else:
            ordered_seats = {}

        if src_groups:
            ev_id = src_groups.groups()[0]
            ev_id_1 = src_groups.groups()[1]
            storage_url = f'https://16tons.qtickets.ru/storage/temp/bundles/{ev_id}/{ev_id_1}.ru.js'
            storage_js = requests.get(storage_url, headers=headers)

            source_seats_list = re.findall(r'var seats=\[(.+?)\];', storage_js.text)
            scheme_config = re.search(r'window.schemeConfig=(.+);', storage_js.text).groups()[0]
            scheme_config = json.loads(scheme_config)

            params = {}
            multiple_params = []
            params_str = re.findall(r'var a=(.+?)var seats=', storage_js.text.replace('\n', ''))
            for param_str in params_str:
                param_str = f'a={param_str}'
                if len(param_str.split(',')) > 4:
                    for param in param_str.split(','):
                        param_name = param.split('=')[0].replace('"', '')
                        param_value = param.split('=')[-1].replace('"', '')
                        params[param_name] = param_value
                else:
                    multiple_param = {}
                    for param in param_str.split(','):
                        param_name = param.split('=')[0].replace('"', '')
                        param_value = param.split('=')[-1].replace('"', '')
                        multiple_param[param_name] = param_value
                    multiple_params.append(multiple_param)

            if source_seats_list:
                for index, source_seats in enumerate(source_seats_list):
                    tickets.extend(
                        self._fetch_seats(source_seats, multiple_params, params, scheme_config, ordered_seats, index))

        result_dict['tickets'] = tickets
        return result_dict

    def _fetch_seats(self, source_seats, multiple_params, params, scheme_config, ordered_seats, index):
        tickets = []

        if '],[' in source_seats:
            source_seats = source_seats.replace('],[', '] [').split(' ')

        if isinstance(source_seats, str):
            seat = source_seats.split(',')
            multiple_info = multiple_params[index]

            sector_id = multiple_info.get(seat[0].replace('[', '').split('-')[0])
            sector_info = scheme_config.get('screens', {}).get('default', {}).get('zones', {}).get(sector_id)
            sector_name = sector_info.get('name')
            nominal_price = multiple_info.get(seat[5])

            hash_object = hashlib.md5(sector_name.encode())
            seat_id = hash_object.hexdigest()

            if all((seat_id, sector_name, nominal_price)) and int(float(nominal_price)) > 0:
                seat_dict = {
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'nominal_price': int(float(nominal_price)),
                    'currency': 'rur',
                    'qty_available': 100,
                    'is_multiple': True,
                }
                tickets.append(seat_dict)
                # print(seat_dict)

        # [a, 4, 1, 0, b, c, d, 59, 546]
        # keys=["zone_id","place","row","disabled","color","price","disabled","x","y"]
        elif isinstance(source_seats, list):
            for s_seat in source_seats:
                seat = s_seat.split(',')

                sector_id = params.get(seat[0].replace('[', '').split('-')[0])
                sector_info = scheme_config.get('screens', {}).get('default', {}).get('zones', {}).get(sector_id)
                sector_name = sector_info.get('name')
                nominal_price = params.get(seat[5])
                if nominal_price.isdigit() is False: continue
                row_number = seat[2]
                seat_number = seat[1]
                seat_id = f'{sector_id}-{row_number};{seat_number}'
                disabled = params.get(seat[6])

                if not ordered_seats.get(seat_id) and all(
                        (seat_id, row_number, seat_number, nominal_price)) and disabled != 'null' \
                        and int(float(nominal_price)) > 0:
                    seat_dict = {
                        'seat_id': seat_id,
                        'sector_name': sector_name,
                        'row_name': row_number,
                        'seat_name': seat_number,
                        'nominal_price': int(float(nominal_price)),
                        'currency': 'rur',
                        'qty_available': 1,
                        'is_multiple': False,
                    }
                    tickets.append(seat_dict)
                    # print(seat_dict)
        return tickets
