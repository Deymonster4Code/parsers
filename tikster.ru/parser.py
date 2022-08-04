import requests
from lxml import etree
from datetime import datetime
import chardet

class Tickster:
    """
                Парсер для площадки https://tikster.ru/concerts
                """

    PARSER_NAME = "tickster"
    EVENTS_HOOK_HELP = 'Пример, https://tikster.ru/concerts'
    TICKETS_HOOK_HELP = "Пример, https://tikster.ru/concerts"
    api_key = ''

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
    }


    url = 'https://tikster.ru/concerts'

    @staticmethod
    def static(api_key):
        Tickster.api_key = api_key


    def get_event_data(self, hook):
        """
                                Получение мероприятий.
                                       Args:
                                           hook: (str) принимает ссылку площадки

                                       Returns:
                                           (list) список мероприятий
                                """
        result = []
        response = requests.get(hook, headers=self.HEADERS)
        if not response.status_code == 200:
            return result
        response.encoding = chardet.detect(response.content)['encoding']
        html = etree.HTML(response.text)
        for event in html.xpath("//div[@class='info-holder']"):
            result.append({
                "event_hook": event.xpath("a/@href")[0],
                "event_name": event.xpath("a/strong")[0].text,
                "event_starts_at": self._get_date_time(event)
            })

        return result

    def _get_date_time(self, event):
        """
                                      Получение даты и врмени мероприятия в формате datetime.
                                             Args:
                                                 event: (object) принимает объект lxml

                                             Returns:
                                                  дата мероприятия
                                      """

        event_hook = event.xpath("a/@href")[0]
        res = requests.get(event_hook, headers=self.HEADERS)
        if not res.status_code == 200:
            return
        res.encoding = chardet.detect(res.content)['encoding']
        html = etree.HTML(res.text)
        event_date = html.xpath("//ul[@class='listing']/li/div/div[1]/span/text()")[0]
        event_day_str = event_date.split(".")[0]
        event_month_str = event_date.split(".")[1]
        event_year_str = event_date.split(".")[2]
        event_time_str = html.xpath("//ul[@class='listing']/li/div/div[2]/span/text()")[0]
        event_starts_at = datetime.strptime(event_day_str + '.' + event_month_str + '.' + event_year_str + ':' + event_time_str, '%d.%m.%Y:%H:%M')

        return event_starts_at


    def get_tickets_data(self, event_hook):
        """
                                       Получение билетов с конкретного мероприятия.
                                              Args:
                                                  event_hook: (str) принимает ссылку на мероприятие

                                              Returns:
                                                  (dict) словарь с билетами
                                       """
        result_dict = {
            'tickets': [],
            'is_stable': True
        }
        response = requests.get(event_hook, headers=self.HEADERS)
        if not response.status_code == 200:
            return result_dict
        response.encoding = chardet.detect(response.content)['encoding']
        html = etree.HTML(response.text)
        self.api_key = html.xpath("//div[@class='date']/script/@src")[0].split("=")[1]
        event_id = html.xpath("//ul[@class='listing']/li/a/@data-eventid")[0]
        result = self._fetch_ticket_data(event_id)
        result_dict['tickets'].extend(result)
        return result_dict



    def _fetch_ticket_data(self, event_id):
        result = []
        url_api = f"https://service.tikster.ru/widget/hall/{event_id}?"
        payload = {'api-key': self.api_key}
        try:
            res = requests.get(url_api, headers=self.HEADERS, params=payload, verify=False)
            res.encoding = chardet.detect(res.content)['encoding']
            data = res.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [500, 502, 534]:
                return None
            raise e
        for ticket in data:
            if not ticket['CanSell']:
                continue
            else:
                seat_id = ticket['cod_hs']
                sector_name = ticket['Name_sec']
                row = ticket['Row']
                place = ticket['Seat']
                try:
                    nominal_price = ticket['amount']
                except KeyError:
                    #print(f"No price in {seat_id}!!!")
                    continue

                if all((seat_id, sector_name, row, place, nominal_price)):
                    seat_dict = {
                        'seat_id': seat_id,
                        'sector_name': sector_name,
                        'row_name': row,
                        'seat_name': place,
                        'nominal_price': nominal_price,
                        'currency': 'rur',
                        'qty_available': 1,
                        'is_multiple': False,
                    }
                    result.append(seat_dict)
        return result












url = 'https://tikster.ru/concerts'
event_hook = 'https://tikster.ru/kipelov'
events = Tickster()
print(events.get_event_data(url))
print(events.get_tickets_data(event_hook))
