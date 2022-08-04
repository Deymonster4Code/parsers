"""
InticketsTS

Используется на источниках:
1 Bastatour
2 Circusaqua (не сделан)
3 Skfo (не сделан)
4 Lihov6 (не сделан)
5 Leningrad (не сделан)
6 Rvtour
7 Bilandima
8 Pelmeny
9 Redglobus
10 Praktikatheatre
11 Maxkorzh
12 Zve
13 Tons16
14 Neoclassica
15 xl.bdva.ru
16 Standupbilet
17 Meladze
18 Bdva
19 Greatcircus
20 Gdeshow
21 Fangid
"""
import hashlib
import json
import re
import time
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse

import requests
from lxml import etree


def intickets_get_tickets_data(buy_url):
    """
    Получаем список билетов
    :param content: страница события
    :param html: разметка схемы
    :param sectors_dict: словарь со секторами
    :return: список билетов
    """

    tickets = []
    result_dict = {
        'tickets': [],
        'is_stable': True,
    }

    hostname = urlparse(buy_url).hostname
    headers = {'authority': hostname}
    response = requests.get(buy_url, headers=headers)
    content = etree.HTML(response.text)
    map_content = content

    show_id = map_content.xpath('//div[@id="schema_body"]/@data-seance')
    if len(show_id) == 0:
        # проверяем есть ли инфа про билеты прямо сразу на странице
        try:
            tickets_info = map_content.xpath('//script[contains(., "sector_nid")]/text()')[0]
            tickets_info_result = re.findall(r'Drupal.settings, (.+?)\);', tickets_info)
        except IndexError:
            return tickets

        tickets = _get_tickets_page(tickets_info_result[0])
        return tickets

    sector_str = map_content.xpath('//script[contains(., "schemaSectorArr")]/text()')[0]
    result = re.findall(r'"schemaSectorArr":({.+?})', sector_str)
    if result is None:
        return tickets

    sectors_dict = json.loads(result[0])

    try:
        url_sess_id = re.findall(r'url_sess_id":"(.+?)"', sector_str)[0]
    except IndexError:
        url_sess_id = ''
    sectors_url = []
    for key, _ in sectors_dict.items():
        sectors_url.append(f'https://{hostname}/ajax/schema/{show_id[0]}/{key}?{url_sess_id}')

    # Многопоточно получаем данные по билетнам
    tickets_tasks = []
    with ThreadPool(5) as pool:
        for sector_url in sectors_url:
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            headers['x-requested-with'] = 'XMLHttpRequest'
            res = pool.apply_async(_get_tickets, (headers, sector_url, sectors_dict))
            tickets_tasks.append(res)

        pool.close()
        pool.join()

        for ticket_task in tickets_tasks:
            task_result = ticket_task.get()

            if type(task_result) is list:
                tickets.extend(task_result)
    result_dict['tickets'] = tickets
    return result_dict


def _get_tickets(headers, sector_url, sectors_dict):
    tickets = []

    content = requests.get(sector_url, headers=headers).json()
    # content = etree.HTML(response.text).json()
    schema_sector_body = content.get('schema_sector_body')
    html = etree.HTML(schema_sector_body)

    tickets_data = html.xpath('//div[@data-seat]/@data-seat')
    # получение билетов с местами
    if len(tickets_data) > 0:
        for ticket in tickets_data:

            # вид данных: 39402316|Б|46|15000|10970009 - id|ряд|место|цена|сектор
            seat_id = ticket.split('|')[0]
            row_name = ticket.split('|')[1]
            seat_name = ticket.split('|')[2]
            nominal_price = ticket.split('|')[3]
            sector_name = sectors_dict.get(ticket.split('|')[4])

            if all((seat_id, sector_name, row_name, seat_name, nominal_price)):
                seat_dict = {
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'row_name': row_name,
                    'seat_name': seat_name,
                    'nominal_price': nominal_price,
                    'currency': 'rur',
                    'qty_available': 1,
                    'is_multiple': False,
                }
                tickets.append(seat_dict)
    # мультибитеты
    else:
        sector_name = content.get('schema_sector_title')

        try:
            nominal_price = html.xpath('//div[@class="cost"]/span/text()')[0]
        except IndexError:
            nominal_price = None

        count = html.xpath('//button[@class="button"]')

        hash_object = hashlib.md5(sector_name.encode())
        seat_id = hash_object.hexdigest()

        if nominal_price is not None and len(count) > 0:
            seat_dict = {
                'seat_id': seat_id,
                'sector_name': sector_name,
                'nominal_price': nominal_price,
                'currency': 'rur',
                'qty_available': len(count),
                'is_multiple': True,
            }
            tickets.append(seat_dict)
            # print(seat_dict)

    return tickets


def _get_tickets_page(tickets_info):
    tickets = []

    event_data = json.loads(tickets_info)
    for _, seats_data in event_data.get('book_unnumbered_only', {}).get('seats').items():
        for _, seat in seats_data.items():
            seat_id = seat.get('sector_nid')
            count = seat.get('amount')
            sector_name = seat.get('title')
            nominal_price = seat.get('cost')

            if all((seat_id, sector_name, count, nominal_price)):
                seat_dict = {
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'nominal_price': nominal_price,
                    'currency': 'rur',
                    'qty_available': int(count),
                    'is_multiple': True,
                }
                tickets.append(seat_dict)
                # print(seat_dict)

    return tickets
