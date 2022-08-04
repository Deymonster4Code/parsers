import requests
from lxml import etree
from datetime import datetime
from arrow.locales import RussianLocale




class KrasnodarCircus:
    """
            Парсер для площадки https://krasnodar-circus.ru/
            """

    PARSER_NAME = "krasnodar-circus.ru"
    EVENTS_HOOK_HELP = 'Пример, https://krasnodar-circus.ru/'
    TICKETS_HOOK_HELP = "Пример, https://krd.kassy.ru/events/cirk/2-5187/hall/"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'host': 'krasnodar-circus.ru'
    }



    def get_event_data(self, hook):
        """Получение мероприятий.

                Args:
                    hook: (str) принимает ссылку на главную страницу площадки

                Returns:
                    (dict) список мероприятий
                """
        result =[]
        response = requests.get(hook)
        events = etree.HTML(response.text)

        title = events.xpath('//div[contains(@field, "tn_text_162704") and starts-with(@class, "tn-atom")]/strong/text()')[0].replace('"', '').strip()
        for event in events.xpath('//div[@class="t774__col t-col t-col_3 t-align_center t-item"]/div/div'):
            day = event.xpath('a/div/div/div/strong')[0].text.split(" ")[0]
            month = RussianLocale.month_names.index(event.xpath('a/div/div/div/strong')[0].text.split(" ")[1].lower())
            for item in event.xpath('div[@class="t774__btn-wrapper t774__paddingbig"]'):
                event_hooks = item.xpath('a/@href')
                event_hours = item.xpath('table/tr/td/text()')
                for event_hook, hour in zip(event_hooks, event_hours):
                    current_date = datetime.now()
                    year = current_date.year
                    if current_date.month > month:
                        year += 1
                    date_time_object_start = datetime.strptime(str(year) + ':' + str(month) + ':' + day + ':' + hour, '%Y:%m:%d:%H:%M')
                    result.append({
                        "event_hook": event_hook,
                        "event_name": title,
                        "event_starts_at": date_time_object_start,
                    })
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
            'is_stable': True,
        }
        session = requests.Session()
        res = session.get(event_hook)
        cookies = session.cookies.get_dict()
        event_id = event_hook.split('event')[1].split('/')[1]
        result = self._get_kassy_tickets_data(event_id, cookies)
        result_dict['tickets'] = result
        return result_dict

    def _get_kassy_tickets_data(self, event_id, cookies):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        params = {
            'ts_id': '2',
            'event_id': event_id
        }
        tickets = []
        content = requests.get('https://krd.kassy.ru/api/hall/', headers=headers, params=params,
                                   cookies=cookies)
        content_json = content.json()
        for section in content_json.get('sections', []):
            sector_name = section.get('section_title')
            for seat in section.get('places'):
                status = seat.get('state')
                if status == 1:
                    seat_id = seat.get('place_id')
                    row_name = seat.get('row')
                    seat_name = seat.get('seat')
                    full_seat_name = f'Место {seat_name}'
                    nominal_price = seat.get('price')
                    sector_name_full = f'{sector_name}, ряд {row_name}'

                    if all((seat_id, row_name, full_seat_name, nominal_price)):
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
        return tickets



#url = 'https://krasnodar-circus.ru/#rec314335224'
#event_hook = 'https://widget2.kassy.ru/auth/krasnodar-circus.ru/?back=/krd/event/5238/'
#events = KrasnodarCircus()
#print(events.get_tickets_data(event_hook))


















