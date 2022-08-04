"""
KassyTS

Используется на источниках:
1 Ptarena
2 Grigoryleps
3 Kassy
4 Pelmeny
5 Makemusic
6 Maxkorzh
7 Zve
8 Standupbilet
9 Meladze
10 Improcom
"""
import base64
import hashlib
import json
import re
from urllib.parse import urlparse


def kassy_get_tickets_data(rw, seance_hook):
    tickets = []

    hostname = urlparse(seance_hook).hostname
    headers = {
        'Host': hostname
    }

    try:
        data_ids = re.findall(r'event/(.+?)/', seance_hook)[0]
    except IndexError:
        data_ids = seance_hook.split('/')[-3]

    ts_id = data_ids.split('-')[0]
    event_id = data_ids.split('-')[-1]
    url = f'https://{hostname}/api/hall/?ts_id={ts_id}&event_id={event_id}&section_id=null&version=dd'
    content_str = rw.get(url, headers=headers)
    content_str = base64.b64decode(content_str.text)
    content_json = json.loads(content_str)

    for section in content_json.get('sections', []):
        sector_name = section.get('section_title')
        for seat in section.get('places'):
            status = seat.get('state')
            if status == 1:
                seat_id = seat.get('place_id')
                row_name = seat.get('row')
                seat_name = seat.get('seat')
                nominal_price = seat.get('price')

                if row_name == '-':
                    row_name = '1'

                if seat.get('row_metric') == 'Стол':
                    if 'стол' not in sector_name:
                        sector_name_full = f'{sector_name} стол {row_name}'
                    else:
                        sector_name_full = f'{sector_name} {row_name}'
                    row_name = '1'
                else:
                    sector_name_full = sector_name

                if all((seat_id, row_name, seat_name, nominal_price)):
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
                    # print(seat_dict)

    # проверяем мультибилеты
    seance_hook = seance_hook.replace('buy', 'sections')
    try:
        content = rw.get_html_page(seance_hook, headers=headers)
    except rw.HTTPError:
        pass

    for block in content.xpath('//table[contains(@class, "table sections")]//tr'):  # групповые
        if len(block.xpath('.//td')) == 0: continue
        sector_data = block.xpath('.//input[contains(@id, "spinner")]')
        if len(sector_data) == 0: continue
        sector_name = block.xpath('.//td[@class="title"]/text()')[0].strip()
        qty = sector_data[0].get('data-count')
        nominal_price = sector_data[0].get('data-cost').replace(' ', '')

        hash_object = hashlib.md5(sector_name.encode())
        seat_id = hash_object.hexdigest()

        if all((sector_name, qty, nominal_price, seat_id)):
            seat_dict = {
                'seat_id': seat_id,
                'sector_name': sector_name,
                'nominal_price': int(float(nominal_price)),
                'currency': 'rur',
                'qty_available': int(qty),
                'is_multiple': True,
            }
            tickets.append(seat_dict)
            # print(seat_dict)

    return tickets
