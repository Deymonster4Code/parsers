import datetime
import time
from datetime import datetime

import requests
from arrow.locales import RussianLocale
from lxml import etree


# class BikeShowParser(GenericParser):
class BikeShowParser:
    """
    Парсер для площадки http://bikeshow.ru/.
    """

    PARSER_NAME = "bikeshow.ru"
    EVENTS_HOOK_HELP = 'Пример, http://bikeshow.ru/category/tickets/'
    TICKETS_HOOK_HELP = "Пример, http://bikeshow.ru/category/tickets/"

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
        link_to_description = html.xpath('//a[@class="continue-reading-link"]')[0].attrib['href']
        response = requests.get(link_to_description)
        html = etree.HTML(response.text)
        link_to_tickets = html.xpath('//a[@class="daria-goto-anchor"]')[0].attrib['href']
        response = requests.get(link_to_tickets)
        html = etree.HTML(response.text)
        now = datetime.now()
        for item in html.xpath('//h5[@class="title"]'):
            start_day = str(item.xpath('span/span')[0].text.split('-')[0])
            end_day = str(item.xpath('span/span')[0].text.split('-')[-1].split(' ')[0])
            month = RussianLocale.month_abbreviations.index(
                item.xpath('span/span')[0].text.split('-')[-1].split(' ')[-1][:3].lower())
            year = str(now.year)
            title = item.xpath('span[@class="event"]')[0].text
            date_time_obj_start = datetime.strptime(year + '-' + str(month) + '-' + start_day + ' ' + '17:00',
                                                    '%Y-%m-%d %H:%M')
            date_time_obj_end = datetime.strptime(year + '-' + str(month) + '-' + end_day + ' ' + '23:30',
                                                  '%Y-%m-%d %H:%M')
            if all((title, date_time_obj_start, date_time_obj_end)):
                result.append({
                    "event_hook": hook,
                    "event_name": title,
                    "event_starts_at": date_time_obj_start,
                    "event_end_at": date_time_obj_end,
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

        response = requests.get(seance_hook)
        html = etree.HTML(response.text)
        link_to_description = html.xpath('//a[@class="continue-reading-link"]')[0].attrib['href']
        response = requests.get(link_to_description)
        html = etree.HTML(response.text)
        link_to_tickets = html.xpath('//a[@class="daria-goto-anchor"]')[0].attrib['href']
        response = requests.get(link_to_tickets)
        html = etree.HTML(response.text)
        for item in html.xpath('//g/@class'):
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            result.append({
                'seat_id': html.xpath('//g[@class="{0}"]'.format(item))[0].attrib['data-sector'],
                'sector_name': html.xpath('//g[@class="{0}"]'.format(item))[0].attrib['data-tooltip'].split('<')[0],
                'nominal_price': int(float(html.xpath('//g[@class="{0}"]'.format(item))[0].attrib['data-min-cost'])),
                'currency': 'rub',
                'qty_available': 16,
                'is_multiple': True,

            })
        result_dict['tickets'] = result
        return result_dict


print(BikeShowParser().get_tickets_data('http://bikeshow.ru/category/tickets/'))
