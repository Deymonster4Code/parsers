import hashlib
import logging
import re
import time
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse

import requests
from lxml import etree

logger = logging.getLogger(__name__)


def kassir_get_tickets_data(iframe_url):
    tickets = []
    result_dict = {
        'tickets': [],
        'is_stable': True,
    }
    hostname = urlparse(iframe_url).hostname
    headers = {
        'Host': hostname,
    }
    try:
        response = requests.get(iframe_url, headers=headers)
        content = etree.HTML(response.text)
        content_for_url = requests.get(iframe_url, headers=headers)
    except:
        return tickets

    try:
        event_id = re.findall(r'/event/(.+)', content_for_url.url)[0].split('?')[0]
    except IndexError:
        event_id = content_for_url.url.split('#')[-1]
    key = re.findall(r'key=(.+)', content_for_url.url)[0].split('&')[0]

    try:
        sessid = re.findall(r'WIDGET_(.+)', content_for_url.url)[0].split('&')[0].split('#')[0]
        sessid = f'WIDGET_{sessid}'
    except:
        sessid = content.xpath('//div[@sessid]/@sessid')[0]

    sectors = content.xpath('//section[@class="sector-list"]//a[@class="sector-item"]')
    tickets_task = []
    with ThreadPool(10) as pool:
        for sector in sectors:
            if not response.status_code == 200:
                result_dict['is_stable'] = False
                time.sleep(5)
                continue
            sector_id = sector.attrib.get('data-sector-id')
            res = pool.apply_async(_fetch_tickets_by_ajax_urls, (
                event_id,
                sector_id,
                sessid,
                key,
                hostname,
            ))
            tickets_task.append(res)

        pool.close()
        pool.join()

        for ticket_task in tickets_task:
            task_result = ticket_task.get()

            if type(task_result) is list:
                tickets.extend(task_result)
    result_dict['tickets'] = tickets
    return result_dict


def _replace_sector_name(sector_name):
    """
    Замена названия сектора на другое (более удобное для использования)
    """
    tmp_sector_name = re.sub(r'\s{2,}', ' ', sector_name).lower().strip()
    sector_alias = {
        'танцпартер': 'Танцевальный партер',
    }
    sector_name = sector_alias.get(tmp_sector_name, sector_name)

    return sector_name


def _fetch_tickets_by_ajax_urls(event_id, sector_id, sessid, key, domain):
    result_data = []

    try:
        headers = {
            'Host': domain,
            'X-Requested-With': 'XMLHttpRequest',
        }
        sector_url = \
            f'https://{domain}/frame/scheme/sector?{sessid}&key={key}&id={event_id}&sector={sector_id}&key={key}'
        sector_info_json = requests.get(sector_url, headers=headers).json()
    except requests.exceptions.Timeout:
        logger.error('KASSIR.RU Sector JSON Connection timed out')
        return None
    except requests.exceptions.HTTPError as e:
        logger.exception(e)
        return None

    raw_xml = sector_info_json.get("view")
    try:
        raw_xml = re.findall(r'\?>(.+)</div>', raw_xml)[0]
        scheme_xml = etree.XML(raw_xml)
    except:
        scheme_xml = None

    sector_name = sector_info_json.get('sector', {}).get('name')
    sector_name = _replace_sector_name(sector_name)
    soes = sector_info_json.get('sector', {}).get('soes', {})
    price_groups = sector_info_json.get('sector', {}).get('price_groups', {})

    # Обработка доступных билетов: создание новых/апдейт существующих.
    if type(soes) is dict and scheme_xml is not None:
        for _, soe_value in soes.items():

            try:
                # Из JSON получаем ID мест и стоимость.
                seat_id = soe_value.get('seatId')

                price_group_id = soe_value.get('lastPriceGroupId')
                price_group = price_groups.get(str(price_group_id))
                nominal_price = price_group.get('price')

                seats_xml = scheme_xml.xpath(
                    './/xmlns:polygon[@kh:id="%s"]' % seat_id,
                    namespaces={
                        'xmlns': "http://www.w3.org/2000/svg",
                        'kh': "urn:ru:pmisoft:kh:svg:1.0"
                    }
                )
                seat_element = seats_xml[0]

                seat_number = seat_element.get('{urn:ru:pmisoft:kh:svg:1.0}number')
                seat_number = clean_place_data(seat_number)
                if '.' in seat_number:
                    seat_number = '1'

                row_number = seat_element.get('{urn:ru:pmisoft:kh:svg:1.0}rowNumber')
                # обработка ряда для александринского театра

                row_number = clean_place_data(row_number, is_row=True)

                # вырезаем слово ряд из номера ряда
                row_number = row_number.lower().replace('ряд', '').strip()

                data_row_name = seat_element.get('{urn:ru:pmisoft:kh:svg:1.0}rowName')

                # проверка есть ли в названии ряда дополнительная информация
                if len(data_row_name.strip()) > 3:
                    if 'ложа' in data_row_name.lower() and 'ряд' in data_row_name.lower():
                        sector_name_full = f'{sector_name.strip()} {data_row_name.lower().split("ряд")[0].strip()}'
                        row_number = data_row_name.lower().split("ряд")[-1].strip().split()[0]
                    elif 'ложа' in data_row_name.lower() and 'ряд' not in data_row_name.lower():
                        sector_name_full = f'{sector_name.strip()} {data_row_name.strip()}'
                    elif 'стол' in data_row_name.lower():
                        sector_name_full = f'{sector_name.strip()} Стол {row_number}'
                        row_number = '1'
                    else:
                        sector_name_full = data_row_name.lower().split('ряд')[0].strip()
                    if sector_name_full == '':
                        sector_name_full = sector_name.strip()
                else:
                    sector_name_full = sector_name.strip()

                # на всякий случай проверим еще раз, если пустая строка, то тогда приравниваем sector_name
                if sector_name_full == "":
                    sector_name_full = sector_name.strip()

                if 'стол' in sector_name_full.lower() and 'ряд' in sector_name_full.lower() and ',' in sector_name_full:
                    sector_item_list = []
                    for i in sector_name_full.split(','):
                        if 'ряд' in i:
                            row_number = i.replace('ряд', '').strip()
                        else:
                            sector_item_list.append(i.strip())
                    sector_name_full = ' '.join(sector_item_list)

                if all((sector_name_full, seat_id, row_number, seat_number, nominal_price)):
                    seat_dict = {
                        'seat_id': seat_id,
                        'sector_name': sector_name_full,
                        'row_name': row_number,
                        'seat_name': seat_number,
                        'nominal_price': nominal_price,
                        'currency': 'rur',
                        'qty_available': 1,
                        'is_multiple': False,
                    }
                    result_data.append(seat_dict)
                    # print(seat_dict)

            except AttributeError as e:
                # logger.exception(e)
                pass

            except IndexError as e:
                # logger.exception(e)
                pass

    elif len(soes) == 0 and type(price_groups) is dict:
        for _, group in price_groups.items():
            nominal_price = int(float(group.get('price')))
            available_count = group.get('count')
            hash_object = hashlib.md5(sector_name.encode())
            seat_id = hash_object.hexdigest()

            if all((sector_name, seat_id, nominal_price, available_count)):
                seat_dict = {
                    'seat_id': seat_id,
                    'sector_name': sector_name,
                    'nominal_price': nominal_price,
                    'currency': 'rur',
                    'qty_available': available_count,
                    'is_multiple': True,
                }
                result_data.append(seat_dict)
                # print(seat_dict)

    return result_data


def clean_place_data(text_string="", is_row=False):
    """
    Чистим строку с местом/рядом от лишнего:
    "12" --> "12"
    "14-а" --> "14-a"
    "Ряд 12" --> "12"
    "Место 15" --> "15"
    "Ложа 19" --> "19"
    is_row:
        1-й ярус Ложа 15 Ряд 1 --> 1
    :param text_string:
    :param is_row очистка ряда
    :return:
    """
    if text_string is None:
        return ""
    elif is_row and 'ряд' in text_string.lower():
        # Изменение для возвращения цифро-буквенных рядов, например, 4а
        # result = re.findall(r'ряд (\d+)', text_string.lower())
        result = text_string.lower().split('ряд')[-1].strip()
        if result:
            return result
        else:
            return text_string
    elif len(text_string) > 0 and text_string[0].isalpha():
        chunks = text_string.split()
        if len(chunks) > 1:
            return " ".join(chunks[1:])
        else:
            return text_string
    else:
        return text_string