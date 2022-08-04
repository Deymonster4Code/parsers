from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import json
import requests
import logging
import time
from fake_useragent import UserAgent
import sys
import os
from dotenv import load_dotenv


# logger = logging.getLogger(__name__)
# logging.basicConfig(format='%(asctime) - %(message)s', level=logging.INFO)
root = logging.getLogger()
root.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


class Aviasales:

    search_url = 'https://tickets-api.aviasales.ru/search/v2/start'
    load_dotenv()
    marker = os.getenv('MARKER') # маркер партнера

    def __init__(self):
        """
        первоначальная инициализация экземпляра
        инициализация сессии
        осуществляется переход в headless режиме на страницу
        получение куки и передача их в сессию
        """
        options = Options()
        options.add_argument("--window-size=1920,1080")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-blink-features")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        chrome_options.add_argument("start-maximized")
        self.browser = webdriver.Chrome(options=options, chrome_options=chrome_options)
        self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => underfined})")
        ua = UserAgent()
        user_agent = ua.random
        self.browser.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        root.info(f'User agent is {user_agent}')
        options.headless = True
        options.add_argument('--headless')
        root.info("Get request to https://www.aviasales.ru/")
        self.browser.get('https://www.aviasales.ru/')
        cookies = self.browser.get_cookies()
        self.session = requests.Session()
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        self.browser.quit()
        root.info("Get all cookies close Chrome")

    def _get_code(self, city):
        """
        :param city: (str) - название города на русском, английском языке
        :return: (str) - код аэропорта
        """
        suggest_url = f'https://suggest.aviasales.ru/v2/places.json?locale=ru_RU&max=7&term={city}&types[]=city&types[]=airport'
        try:
            res = self.session.get(suggest_url)
            if res.status_code == 200 and res.text != '[]\n':
                res_json = res.json()
                code = res_json[0].get('code')
                return code
            elif res.status_code == 200 and res.text == '[]\n' or res.status_code == 400:
                root.error(f'Empty response, wrong request city for {city}')
                return f'Empty response, wrong request city - {city}'
        except Exception as error:
            root.error(f'Error getting CODE  {error}')


    def get_search_id(
            self, origin, destination, date1, adults, date2=None, children=0, infants=0, trip_class='Y',
            direct_flights=True, brand_ticket=True):
        """

        :param origin: (str) город отправления
        :param destination: (str) город назначения
        :param date1: (str)  дата билета вылета в формате 2022-07-10  год-месяц-день
        :param adults: (int) количество взрослых
        :param date2: (str)  дата обратного билета в формате 2022-07-10  год-месяц-день для билета в один конец по
        умолчанию в None
        :param children: (int) количество детей по умолчанию 0
        :param infants: (int) количество младенцев по умолчанию 0
        :param trip_class: (str) тип билета по умолчанию эконом класс Y, W - комфорт, C - бизнес, F - первый
        :param direct_flights: (bool) опция прямого перелета, по умолчанию True
        :param brand_ticket:

        :return:  search_id: (str) зашифрованный поисковый запрос (для дальнейшего применения)
        """
        origin_code = self._get_code(origin)
        destination_code = self._get_code(destination)
        root.info("Get code of airports")
        if date2:
            root.info("Search for round trip tickets")
            json_data = {
                'search_params': {
                    'directions': [
                        {
                            'origin': origin_code,
                            'destination': destination_code,
                            'date': date1,
                        },
                        {
                            'origin': destination_code,
                            'destination': origin_code,
                            'date': date2,
                        },
                    ],
                    'passengers': {
                        'adults': adults,
                        'children': children,
                        'infants': infants,
                     },
                    'trip_class': trip_class,
                    },
                    'client_features': {
                        'direct_flights': direct_flights,
                        'brand_ticket': brand_ticket,
                        'top_filters': True,
                        'badges': True,
                        'tour_tickets': True,
                        'assisted': True,
                    },
                        'marker': '360605',
                        'market_code': 'ru',
                        'citizenship': 'ru',
                        'currency_code': 'rub',
                        'languages': {
                                'ru': 1,
                                },
                        'debug': {
                            'experiment_groups': {
                                                    'serp-exp-virtualInterline': 'on',
                                                    'serp-exp-pinFlight': 'on',
                                                    'serp-exp-fares': 'on',
                                                    'serp-exp-baggageUpsale': 'on',
                                                    'asb-exp-footerButton': 'off',
                                                    'asb-exp-ticketsVersion': 'v2',
                                                    'asb-exp-insurance': 'separate',
                                                    'avs-exp-downgradedGates': 'on',
                                                    'asb-exp-feedback': 'form',
                                                    'avs-exp-comparisonWidget': 'on',
                                                    'avs-exp-aa': 'off',
                                                    'ex-exp-autosearchWidget': 'on',
                                                    'serp-exp-travelRestrictions': 'on',
                                                    'avs-exp-checkbox': 'tvil',
                                                    'guides-exp-travelMapBanner': 'treatment-labels',
                                                    'guides-exp-feed': 'off',
                                                    'serp-exp-marketingOperatingCarrier': 'on',
                                                    'prem-exp-webFloatingElement': 'new',
                                                    'b2b-exp-signin': 'on',
                                                    'avs-exp-newAutocomplete': 'on',
                                                    'serp-exp-softFilters': 'on',
                                                    'serp-exp-scoring': 'on',
                                                    'serp-exp-flightTermsMerge': 'on',
                                                    'serp-exp-ota': 'on',
                                                },
                                },
                                'brand': 'AS',
                            }
        else:
            root.info("Search one way trip tickets")
            json_data = {
                'search_params': {
                    'directions': [
                        {
                            'origin': origin_code,
                            'destination': destination_code,
                            'date': date1,
                        }
                    ],
                    'passengers': {
                        'adults': adults,
                        'children': children,
                        'infants': infants,
                    },
                    'trip_class': trip_class,
                },
                'client_features': {
                    'direct_flights': direct_flights,
                    'brand_ticket': brand_ticket,
                    'top_filters': True,
                    'badges': True,
                    'tour_tickets': True,
                    'assisted': True,
                },
                'marker': '360605',
                'market_code': 'ru',
                'citizenship': 'ru',
                'currency_code': 'rub',
                'languages': {
                    'ru': 1,
                },
                'debug': {
                    'experiment_groups': {
                        'serp-exp-virtualInterline': 'on',
                        'serp-exp-pinFlight': 'on',
                        'serp-exp-fares': 'on',
                        'serp-exp-baggageUpsale': 'on',
                        'asb-exp-footerButton': 'off',
                        'asb-exp-ticketsVersion': 'v2',
                        'asb-exp-insurance': 'separate',
                        'avs-exp-downgradedGates': 'on',
                        'asb-exp-feedback': 'form',
                        'avs-exp-comparisonWidget': 'on',
                        'avs-exp-aa': 'off',
                        'ex-exp-autosearchWidget': 'on',
                        'serp-exp-travelRestrictions': 'on',
                        'avs-exp-checkbox': 'tvil',
                        'guides-exp-travelMapBanner': 'treatment-labels',
                        'guides-exp-feed': 'off',
                        'serp-exp-marketingOperatingCarrier': 'on',
                        'prem-exp-webFloatingElement': 'new',
                        'b2b-exp-signin': 'on',
                        'avs-exp-newAutocomplete': 'on',
                        'serp-exp-softFilters': 'on',
                        'serp-exp-scoring': 'on',
                        'serp-exp-flightTermsMerge': 'on',
                        'serp-exp-ota': 'on',
                    },
                },
                'brand': 'AS',
            }

        try:
            response = self.session.post(self.search_url, json=json_data)
            if response.status_code == 200:
                res_json = response.json()
                search_id = res_json.get('search_id')
                root.info("Getting search_id successfuly")
                return search_id
        except Exception as error:
            root.error(f'Error getting request for search_id  {error}')


    def get_tickets_data(self, search_id):
        """

        :param search_id: (str) поисковый запрос
        :return: добавляет в список results словари с билетами и сведениями о полетах
        """
        results = []
        params = {
            'uuid': search_id,
        }
        url_results = 'http://api.travelpayouts.com/v1/flight_search_results'

        end = False
        while not end:
            res_results = self.session.get(url_results, params=params)
            root.info("Request for tickets - ok")
            try:
                res_json = res_results.json()[0]

                try:
                    for proposal in res_json.get('proposals'):
                        for key, value in proposal.get('terms').items():
                            agent_id = key
                            agent_name = res_json.get('gates_info').get(agent_id).get('label')
                            agent_payments_methods = res_json.get('gates_info').get(agent_id).get('payment_methods')
                            price = value.get('price')
                            url_id = value.get('url')
                        segment = [proposal.get('segment')[0].get('flight'),
                                   proposal.get('segment')[1].get('flight')]
                        stops_airports = [proposal.get('stops_airports')]
                        carriers = [proposal.get('carriers')]
                        segments_airports = [proposal.get('segments_airports')]
                        is_direct = proposal.get('is_direct')
                        validating_carrier = proposal.get('validating_carrier')
                        if all((agent_id, agent_name, agent_payments_methods, price, url_id, segment, stops_airports,
                               carriers, segments_airports, is_direct, validating_carrier)):
                            proposal_dict = {
                                'ticket':
                                    {'price': price,
                                        'agent_id': key,
                                        'agent_name': agent_name,
                                        'agent_payments_methods': agent_payments_methods,
                                        'url_id': url_id,
                                        'is_direct': is_direct
                                     },

                                'flight':
                                    {'segment': segment,
                                        'stops_airports': stops_airports,
                                        'carriers': carriers,
                                        'segments_airports': segments_airports,
                                        'validating_carrier': validating_carrier
                                    }
                            }
                            root.info("Tickets data added to list results")
                            results.append(proposal_dict)
                except TypeError:
                    #root.error("Wrong response format")
                    pass

            except IndexError:
                end = True
                root.info("The end of responses")

        with open('data.json', 'w') as file:
            json.dump(results, file)
        return results

    def get_url(self, search_id, url_id):
        """

        :param search_id: (str)   - поисковый запрос из get_search_id
        :param url_id: (str) - поле url_id из результатов поиска
        :return: (str) - ссылка на покупку билета - время жизни ссылки 15 минут!!!
        После чего требуется произвести поиск заново для получения актуальных цен!!!
        """
        url = f'http://api.travelpayouts.com/v1/flight_searches/{search_id}/clicks/{url_id}.json?marker={self.marker}'
        res = requests.get(url)
        res_json = res.json()
        if res_json.get('method') == 'GET':
            url_ticket = res_json.get('url')
            print(url_ticket)
            return url_ticket
        else:
            print('Method POST detected!')

def main():
    parser = Aviasales()
    search_id = parser.get_search_id(
         origin='Москва', destination='Стамбул', date1='2022-07-11', adults=2, date2='2022-07-20')

    print(search_id)
    parser.get_tickets_data(search_id=search_id)
    parser.get_url(search_id, '700020')
    sys.stdout = Aviasales('log.txt', 'a')


if __name__ == '__main__':
    main()










