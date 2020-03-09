import os
import json
from collections import defaultdict

import pymongo


HERE = os.path.dirname(__file__)


def connect_db(mongo_db_url, db, collection):
    mongo_client = pymongo.MongoClient(mongo_db_url)
    mongo_db = mongo_client[db]
    collection = mongo_db[collection]
    return collection


# pipeline = [
#     {'$unwind': '$samples'},
#     {'$match': {'samples.item_name': '矫正视力(左)'}},
#     {'$group': {'_id': "$samples.value", 'count': {'$sum': 1}}},
#     {'$sort': {'count': -1}}
# ]

def samples_value_counter(the_collection):
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
    for c in the_collection:
        samples = c.get('samples')
        if not samples:
            continue
        for sample in samples:
            data = defaultdict(int)
            group_name = sample['group_item_name']
            item_name = sample['detail_item_name']
            if item_name != '小结':
                value = sample['exam_result']
                if len(value) > 20:
                    value = f'{value[:20]}...'
                res.setdefault(f'group_name: {group_name}, item_name:{item_name}', data)
                res[f'group_name: {group_name}, item_name:{item_name}'][value] += 1
    return res
