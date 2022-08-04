import datetime
import re
from datetime import datetime

import requests
from arrow.locales import RussianLocale
from lxml import etree

from roofmusicgroup.core_kassir import kassir_get_tickets_data


# class RoofMusicGroupEvent(GenericParser):
class RoofMusicGroupParser:
    """
    Парсер для площадки https://roofmusicgroup.ru/concerts/spb/.
    """

    PARSER_NAME = "roofmusicgroup.ru"
    EVENTS_HOOK_HELP = 'Пример, https://roofmusicgroup.ru/concerts/spb/'
    TICKETS_HOOK_HELP = "Пример, https://roofmusicgroup.ru/concerts/295/"

    HEADERS = {'authority': ''}

    def get_event_data(self, hook):
        """Получение мероприятий.

        Args:
            hook: (str) принимает ссылку площадки

        Returns:
            (dict) список мероприятий
        """
        result = []
        now = datetime.now()
        response = requests.get(hook)
        html = etree.HTML(response.text)
        for concert in html.xpath('//div[@class="concert-item"]'):
            year = str(now.year)
            month = self._get_event_date_month(concert)
            day = self._get_event_date_number(concert)
            start_at = self._get_event_date_time(concert)
            date_time_obj = datetime.strptime(year + '-' + str(month) + '-' + day + ' ' + start_at, '%Y-%m-%d %H:%M')
            if all((self._get_event_link(concert), self._get_event_title(concert), date_time_obj)):
                result.append({
                    "event_hook": 'https://roofmusicgroup.ru' + self._get_event_link(concert),
                    "event_name": self._get_event_title(concert),
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
        if '/frame/event/' in seance_hook:
            a = kassir_get_tickets_data(seance_hook)
            return a
        return {}

    def _get_event_title(self, soup):
        """Получение название мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        data = soup.xpath("div[@class='event-head']/a")[0].text
        return data

    def _get_event_link(self, soup):
        """Получение id мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        return soup.xpath('div[2]/a/@href')[0]

    def _get_event_date_number(self, soup):
        """Получение дня проведение мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        return soup.xpath("div/div[@class='date']/b")[0].text

    def _get_event_date_month(self, soup):
        """Получение месяц проведение мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        month = soup.xpath("div/div[@class='date']/span[@class='month']")[0].text
        return RussianLocale.month_abbreviations.index(month[:3].lower())

    def _get_event_date_time(self, soup):
        """Получение время проведение мероприятие.

        Args:
            soup: (str) принимает текст

        Returns:
            (str)
        """
        time = soup.xpath("div/div[@class='date']/span")[1].text
        re_result = re.search(r"начало\s*в\s*(.*)", time)
        if not re_result:
            return ''
        sector_name = re_result[1]
        return sector_name

