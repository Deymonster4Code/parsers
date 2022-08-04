from datetime import datetime
from pprint import pprint

import requests
from lxml import etree


class BaletMoskvaParser:

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку на главную страницу площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        response = requests.get(hook)
        events = etree.HTML(response.text)
        for event in events.xpath('//div[@class="ui-tabs-panel ui-widget-content ui-corner-bottom"]/table/tbody/tr'):
            title = event.xpath('td')[2].xpath('div/a')[0].text
            event_hook = str(event.xpath('td')[3].xpath('a/@href')[0])
            start_hour = event.xpath('td/br')[0].tail.strip()
            start_day = event.xpath('td')[0].text.strip().split('.')[0]
            start_month = event.xpath('td')[0].text.strip().split('.')[1].split(',')[0]
            # calendar.month_name[int(start_month)]
            start_year = datetime.now().year
            if datetime.now().month > int(start_month):
                start_year += 1
            date_time_object_start = datetime.strptime(str(start_year) + start_month + start_day + start_hour,
                                                       '%Y%m%d%H:%M')
            result.append({
                "event_hook": event_hook,
                "event_name": title,
                "event_starts_at": date_time_object_start,
            })
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
        # result.append(intickets_get_tickets_data(seance_hook))

        # response = requests.get(seance_hook)
        # html = etree.HTML(response.text)
        # href = html.xpath('//a[@class="bay"]')[0].attrib['href']
        # seance_id = href.split('/')[-1]
        # url_scheme = 'https://iframeab-pre0236.intickets.ru/node/'
        # return intickets_get_tickets_data(url_scheme + seance_id)
        # https://gorkassa.ru/events/vodevilprodoljenie-4741/
        # 'https://iframeab-pre0236.intickets.ru/node/11874741'


pprint(BaletMoskvaParser().get_tickets_data('https://iframeab-pre2070.intickets.ru/seance/11906153'))
