import datetime
from datetime import datetime

import requests
from arrow.locales import RussianLocale
from lxml import etree

from gorkassa.core_intickets import intickets_get_tickets_data


class GorKassParser:
    """
    Парсер для площадки https://gorkassa.ru/.
    """

    PARSER_NAME = "gorkassa.ru"
    EVENTS_HOOK_HELP = 'Пример, https://gorkassa.ru/category-afisha-teatra-armena-dzhigarhanyana/'
    TICKETS_HOOK_HELP = "Пример, https://gorkassa.ru/events/vojd-krasnokojih-1203/"

    HEADERS = {'authority': ''}

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
        max_page = html.xpath('//div[@class="buttons"]/a')[0].attrib['data-nav-page-count']
        current_page = 1
        page = '?PAGEN_3='
        ajax_id = '&bxajaxid=Y&_='
        while current_page <= int(max_page):
            url = hook + page + str(current_page) + ajax_id
            response = requests.get(url)
            html = etree.HTML(response.text)
            current_page += 1
            for concert in html.xpath('//div[@class="event_content"]'):
                year = concert.xpath('a/div/div/div[@class="ic-year"]')[0].text
                month = concert.xpath('a/div/div/div[@class="ic-month"]')[0].text[:3].lower()
                day = concert.xpath('a/div/div/div[@class="ic-day"]')[0].text
                time = concert.xpath('a/div/div/div[@class="ic-time"]')[0].text
                date_time_obj = datetime.strptime(
                    year + '-' + str(RussianLocale.month_abbreviations.index(month)) + '-' + day + ' ' + time,
                    '%Y-%m-%d %H:%M')
                event_hook = concert.xpath('a/@href')[0]
                event_name = concert.xpath('a/@title')[0]
                if all((event_hook, event_name, date_time_obj)):
                    result.append({
                        "event_hook": 'https://gorkassa.ru' + event_hook,
                        "event_name": event_name,
                        "event_starts_at": date_time_obj,
                    })
        return result

    def get_tickets_data(self, seance_hook, starts_at=None, provider_data={}, event_place_id=None):
        """Получение билетов c конкретного мероприятия.

        Args:
            seance_hook: (str) принимает ссылку определенного мероприятия

        Returns:
            (dict)
        """
        response = requests.get(seance_hook)
        html = etree.HTML(response.text)
        href = html.xpath('//a[@class="bay"]')[0].attrib['href']
        seance_id = href.split('/')[-1]
        url_scheme = 'https://iframeab-pre0236.intickets.ru/node/'
        return intickets_get_tickets_data(url_scheme + seance_id)
