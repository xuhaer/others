import os
import json
from collections import defaultdict

import pymongo


def connect_db():
    mongo_client = pymongo.MongoClient(os.environ.get('Mongo_DB'))
    mongo_db = mongo_client["test"]
    collection = mongo_db['boc_appointment']
    return collection

collection = connect_db()

# pipeline = [
#     {'$unwind': '$samples'},
#     {'$match': {'samples.item_name': '矫正视力(左)'}},
#     {'$group': {'_id': "$samples.value", 'count': {'$sum': 1}}},
#     {'$sort': {'count': -1}}
# ]

def samples_value_counter():
    '''
        生成以item_name为key, 以samples值的统计值为值的函数，后期考虑成用pymongo的聚合函数
        如:
        {
            "身高": {
                "177": 100,
                "175": 50
            },
            "体重": {
                "60": 130,
                "70": 20
            }
        }
    '''
    res = {}
    for c in collection.find({"hospital": '连云港第一人民医院'}):
        samples = c.get('samples')
        if not samples:
            continue
        for sample in samples:
            data = defaultdict(int)
            group_name = sample['group_item_name']
            item_name = sample['detail_item_name']
            if item_name != '小结':
                value = sample['exam_result']
                res.setdefault(f'{group_name}@_@{item_name}', data)
                res[f'{group_name}@_@{item_name}'][value] += 1
    return res

with open('oringin_data_counter.json', 'w') as f:
    json.dump(samples_value_counter(), f, ensure_ascii=False, indent=2)