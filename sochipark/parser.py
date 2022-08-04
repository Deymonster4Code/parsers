from datetime import datetime, timedelta

import requests
from lxml import etree


class SochiParkParser:
    """
    Парсер для площадки https://www.sochipark.ru.

    """
    PARSER_NAME = "sochipark.ru"
    EVENTS_HOOK_HELP = 'Пример, https://www.sochipark.ru'
    TICKETS_HOOK_HELP = "Пример, https://www.sochipark.ru/tickets/"

    cookies = {
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://www.sochipark.ru/programma/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    params = (
        ('tab', 'ONLINE'),
    )

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку на главную страницу площадки

        Returns:
            (list) список мероприятий
        """
        response = requests.get(hook, headers=self.headers, params=self.params, cookies=self.cookies)
        data = etree.HTML(response.text)
        title = 'Сочи Парк 10:00 - 22:00'
        event_hook = hook + str(data.xpath('//div[@class="button"]/a/@href')[0])
        start_hour = data.xpath('//a[@class="work-time"]/span')[0].tail.split(' ')[1]
        finish_hour = data.xpath('//a[@class="work-time"]/span')[0].tail.split(' ')[3]
        # вызываем метод который получает событие с  финишней датой
        result = self._get_finish_date(event_hook, title, start_hour, finish_hour)
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов c мероприятия.

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
        response = requests.get(seance_hook, headers=self.headers, params=self.params, cookies=self.cookies)
        if response.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif response.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict
        data = etree.HTML(response.text)
        ticket_list = data.xpath('//div[@class="grid-row"]/div/div[@class="js-ticket-card ticket-card can-buy"]')
        for ticket in ticket_list:
            ticket_type = ticket.xpath('div/div[@class="type"]')[0].text
            ticket_name = ticket.xpath('div[@class="name"]')[0].text
            seat_id = str(ticket.xpath('div/@data-id')[0])
            nominal_price = ticket.xpath('div[@class="price"]')[0].text.split(' ')[0].replace(' ', '')
            if all((ticket_type, ticket_name, seat_id, nominal_price)):
                result.append({
                    'seat_id': seat_id,
                    'sector_name': f'({ticket_type}) ' + ticket_name,
                    'nominal_price': int(nominal_price),
                    'currency': 'rub',
                    'qty_available': 1,
                    'is_multiple': True,

                })
                result_dict['tickets'] = result
        return result_dict

    def _get_finish_date(self, event_hook, title, start_hour, finish_hour):
        """Получение событий с датой окончания мероприятия.

        Returns:
            (list)
        """
        cookies = {
            'BITRIX_SM_SALE_UID': '2769255',
            'PHPSESSID': '19a081d690061513a2d4046ecc019fc3',
            'BITRIX_SM_lang': 'ru',
            'cookies-confirm': '1',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Bx-ajax': 'true',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.sochipark.ru',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        params = (
            ('mode', 'class'),
            ('c', 'sibirix:program'),
            ('action', 'list'),
        )
        # сначала берем текущую дату
        result = []
        current_date = datetime.now()
        while True:
            day = str(current_date.day)
            month = str(current_date.month)
            year = str(current_date.year)
            # соединяем в нужный формат части даты день, месяц и год
            date = '{0}.{1}.{2}'.format(day, month, year)
            data = {
                'post[date]': date,
                'SITE_ID': 's1',
                'sessid': 'af3e6c688720a000ed500b8ce19917f1'
            }
            # делаем запрос на день с  определнной датой
            response = requests.post('https://www.sochipark.ru/bitrix/services/main/ajax.php', headers=headers,
                                     params=params, cookies=cookies, data=data)
            # берем json
            data = response.json()
            # проверяем возвращается ли в json нужное поле, если да то добовляем 1 день к current_date
            # так же данные о евенте сохраняем в result и снова проверяем
            if data['data']['today']['parkWorkTime']:
                date_time_object_start = datetime.strptime(str(current_date.date()) + start_hour, '%Y-%m-%d%H:%M')
                date_time_object_end = datetime.strptime(str(current_date.date()) + finish_hour, '%Y-%m-%d%H:%M')
                result.append({
                    "event_hook": event_hook,
                    "event_name": title,
                    "event_starts_at": date_time_object_start,
                    "event_end_at": date_time_object_end,
                })
                current_date += timedelta(days=1)
                continue
            # если нужное поле не возращается, значит в этот день и дальше не запланированы события
            # следоватлеьно не надо дальше проверять, возвращаем result
            else:
                return result
