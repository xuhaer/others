import json
from itertools import groupby, combinations_with_replacement
from collections import defaultdict

import requests


URL = 'http://www.sf-express.com/sf-service-owf-web/service/rate/newRates?origin=A{}000&dest=A{}000&weight={}&time=2019-07-22T16%3A30%3A00%2B08%3A00&volume=0&queryType=2&lang=sc&region=cn&translate='


with open('./mess/cities.json') as f:
    CITIES = json.load(f)

min_cities = {}
for province, areas in groupby(CITIES, key=lambda num: num[:2]):
    cities = list(areas)
    name, query_area = CITIES[cities[0]], cities[5]
    min_cities[name] = query_area


def get_data(o_k, d_k, o_v, d_v, weight):
    url = URL.format(o_v, d_v, weight)
    try:
        resp = requests.get(url).json()
    except Exception:
        print(f'查询{o_k}————{d_k}价格出错!!!!')
    else:
        if not resp:
            return get_data(o_k, d_k, int(o_v) + 1, int(d_v) + 1, weight)
    return resp


res = {}
for (o_k, o_v), (d_k, d_v) in list(combinations_with_replacement(min_cities.items(), 2)):
    k = f'{o_k}————{d_k}价格'
    data1 = get_data(o_k, d_k, o_v, d_v, weight=1)
    data2 = get_data(o_k, d_k, o_v, d_v, weight=2)
    if not (data1 and data2):
        print(f'查询{o_k}————{d_k}价格出错!!!!')
        continue
    res[k] = {'首重': data1[0]['freight'], '续重': data2[0]['freight'] - data1[0]['freight']}
