import requests
from datetime import datetime
import json


class TicketsVolley:
    """
                Парсер для площадки https://tickets.volley.ru/ru/tickets//#/afisha/event/0/all
                """
    PARSER_NAME = "ticketsvolley"
    EVENTS_HOOK_HELP = 'Пример, https://tickets.volley.ru/ru/tickets//#/afisha/event/0/all'
    TICKETS_HOOK_HELP = "Пример, https://tickets.volley.ru/ru/tickets//#/afisha/event/0/all"

    headers = {'Content-Type': 'application/json; charset=UTF-8'}

    url_event_base = 'https://tickets.volley.ru/ru/tickets/#/buy/event/'
    url = 'https://tickets.volley.ru/ru/tickets//#/afisha/event/0/all'
    url_view = 'https://volley2022.site.v3.ubsystem.ru/event/main/view'
    url_index = 'https://volley2022.site.v3.ubsystem.ru/event/main/index'


    def get_event_data(self, hook):
        """
                        Получение мероприятий.
                               Args:
                                   hook: (str) принимает ссылку площадки

                               Returns:
                                   (list) список мероприятий
                        """
        result = []
        payload = {"filter": {"with_times": True}, "sort": False}
        response = requests.post(self.url_index, data=json.dumps(payload), headers=self.headers)
        if not response.status_code == 200:
            return result
        events_content = response.json()
        for event in events_content:
            if event['sales_status'] == 'AVAILABLE':
                event_id = event['id']
                event_name = event['title']
                event_date = event['date']
                event_time = event['time']
                if all((event_id, event_name, event_date, event_time)):
                    result.append({
                        "event_hook": self.url_event_base + event_id + '/' + event_date + '/' + event_time,
                        "event_name": event_name,
                        "event_starts_at": datetime.strptime(event_date + ':' + event_time, '%Y-%m-%d:%H:%M:%S')
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
        result = []
        event_id = event_hook.split("event")[1].split("/")[1]
        event_date = event_hook.split("event")[1].split("/")[2]
        event_time = event_hook.split("event")[1].split("/")[3]
        payload = {"event_id": event_id, "date": event_date, "time": event_time}
        resp = requests.post(self.url_view, data=json.dumps(payload), headers=self.headers)
        if resp.status_code in [404]:
            result_dict['is_stable'] = True
            return result_dict
        elif resp.status_code in [502, 403]:
            result_dict['is_stable'] = False
            return result_dict

        event_content = resp.json()
        if event_content['sales_status'] == 'AVAILABLE':
            for ticket in event_content['tariff']['items']:
                if not ticket['limit'] == '0':
                    seat_id = ticket['social_category_id']
                    sector_name = ticket['social_category_title']
                    seat_name = ticket['social_category_title']
                    nominal_price = ticket['price']
                    qty_available = ticket['limit']
                    if all((seat_id, sector_name, seat_name, nominal_price, qty_available)):
                        seat_dict = {
                            'seat_id': seat_id,
                            'sector_name': sector_name,
                            'row_name': '1',
                            'seat_name': seat_name,
                            'nominal_price': nominal_price,
                            'currency': 'rur',
                            'qty_available': qty_available,
                            'is_multiple': True,
                            }
                        result.append(seat_dict)

        result_dict['tickets'] = result
        return result_dict



url = 'https://tickets.volley.ru/ru/tickets/#/buy/event/1/2022-08-26/20:00:00'
events = TicketsVolley()
print(events.get_tickets_data(url))





