import json
import os

import pymongo
import pandas as pd

from custom_functions import to_str, to_float, find_numeric


with open('st_map_after_comfirmed.json') as f:
    MAPS = json.load(f)


def connect_db():
    mongo_client = pymongo.MongoClient(os.environ.get('Mongo_DB'))
    mongo_db = mongo_client["test"]
    collection = mongo_db['yz_appointment']
    return collection


def to_std_value(function_name, value):
    '''参见 custom_functions.py '''
    try:
        std_value = globals().get(function_name)(value)
    except ValueError:
        raise ValueError('非法的 function_name 或其他错误!') from None
    return std_value


def to_std_samples(raw_mongo_samples):
    '''
        根据人工确认后的配置信息，将 MongoDB 中的samples数据转换为标准key-value数据
        如: [{"group_name": "一般情况", "item_name": "身高", "value": "177"},
             {"group_name": "一般情况", "item_name": "体重", "value": "60"}]
            --> {'height': 177, 'weight': 60}
    '''
    std_samples = {}
    for sample in raw_mongo_samples:
        group_name, item_name, value = sample['group_name'], sample['item_name'], sample['value']
        st_map_ = [m for m in MAPS if (m['group_name'] == group_name and m['item_name'] == item_name)]
        assert len(st_map_) == 1
        st_map = st_map_[0]
        std_key = st_map['std_name']['name']
        function_name = st_map['function']
        std_value = to_std_value(function_name, value)
        # todo 有可能几个item_name对应同一个 std_key: 这时后者的值会覆盖掉前者的值
        # 假如有俩item_name均对应为同一个std_key，如： 身高: '177', '身高1': '178' --> {'height': 178}
        if not std_key: # 严格来讲最终导入数据的时候配置json里面不可能没有 std_name
            std_samples[item_name] = std_value
        else:
            std_samples[std_key] = std_value
    return std_samples


def main():
    collection = connect_db()
    document = collection.find()
    excel_data = []
    for row in document:
        _id = row['_id']
        std_samples = to_std_samples(row['samples'])
        # todo 将标准 std_samples 写入mongo_db
        row.update(std_samples)
        for k in ['summary', 'summarize', 'advise', 'suggest', 'pe_result', 'samples']:
            try:
                del row[k]
            except KeyError:
                pass
        excel_data.append(row)
    return excel_data


excel_data = main()
df = pd.DataFrame(excel_data)
df.to_excel('temp.xlsx')
