import re
import json

from collections import Counter
from operator import itemgetter

import jieba
import pandas as pd
import numpy as np


with open('./excel_eval/st.json') as f:
    SAMPLETYPE = json.load(f)


with open('./excel_eval/refRange.json') as f:
    REFRANGE = json.load(f)


def name_similarity(origin_name):
    similar_list = []
    for st in SAMPLETYPE:
        st_name_str = f"{st['nameChs']} {st['name']} {st['nameChsAlts']}"
        st_name_words = set(jieba.cut(st_name_str)) - {'-', ' ', '_', ')', '('}
        origin_name_words = set(jieba.cut(origin_name)) - {'-', ' ', '_', ')', '('}
        sim = round(len(st_name_words & origin_name_words) / max(len(st_name_words), len(origin_name_words)), 2)
        origin_name_words_eng = set(re.findall(r'[a-zA-Z1-9]{2,}', origin_name))
        st_name_words_eng = set(jieba.cut(st['name'])) - {'-', ' ', '_', ')', '('}
        eng_name_sim = round(len(st_name_words_eng & origin_name_words_eng) / max(len(st_name_words_eng), len(origin_name_words_eng)), 2)
        sim += eng_name_sim
        if sim > 0:
            similar_list.append([sim, st])
    return similar_list


def dataType_similarity(similarity, most_common_type):
    if most_common_type == 'numeric':
        for index, (sim, st) in enumerate(similarity):
            if st['dataType'] in ['[float]', 'float', 'int']:
                similarity[index][0] += 0.2
    elif most_common_type == 'str':
        for index, (sim, st) in enumerate(similarity):
            if st['dataType'] == 'text':
                similarity[index][0] += 0.2
    else:
        pass
    return similarity


def most_common_data_similarity(similarity, most_common_data_set):
    for index, (sim, st) in enumerate(similarity):
        if most_common_data_set & set(json.loads(st['allowedDataRange'])):
            similarity[index][0] += 0.2
    return similarity


def data_value_similarity(similarity, percent_70):
    for index, (sim, st) in enumerate(similarity):
        allow_min, allow_max = REFRANGE.get(st['name'], [999, -999])
        if percent_70[0] > allow_min and percent_70[1] < allow_max:
            similarity[index][0] += 0.1
    return similarity


def unit_similarity(similarity, unit):
    for index, (sim, st) in enumerate(similarity):
        if unit == st['unit']:
            similarity[index][0] += 0.2
    return similarity


def predict(origin_name, most_common_type=None,
            most_common_data=None,
            unit=None, percent_70=None):
    assert isinstance(origin_name, str)
    similarity = name_similarity(origin_name)
    if most_common_type:
        similarity = dataType_similarity(similarity, most_common_type)
    if most_common_data:
        similarity = most_common_data_similarity(similarity, most_common_data)
    if unit:
        similarity = unit_similarity(similarity, unit)
    if percent_70:
        similarity = data_value_similarity(similarity, percent_70)
    return similarity


def cell_type(x):
    """判断某列中某cell的数据类型"""
    try:
        xx = float(x)
    except ValueError:
        return 'str'
    else:
        if np.isnan(xx):
            return 'nan'
        else:
            return 'numeric'


def main(column, col, confirmed_st, unit=None):
    col_info = {}
    if column in confirmed_st:
        col_info['相似度'] = confirmed_st[column]
        col_info['确认情况'] = '已确认'
        return col_info
    cnt = Counter(col.map(cell_type))
    col_info['值的类型'] = dict(cnt)
    most_common_type, *v = cnt.most_common(1)[0]
    if most_common_type == 'numeric':
        test_col = pd.to_numeric(col, errors='coerce')
        test_col = test_col.fillna(method='ffill')
        test_col = test_col.fillna(method='bfill')
        col_min, col_max = test_col.min(), test_col.max()
        percent_70 = round(np.percentile(test_col, 15), 2), round(np.percentile(test_col, 85), 2)
        col_info['最小值'], col_info['最大值'] = round(col_min, 2), round(col_max, 2)
        col_info['70%的值分布于'] = percent_70
        similarity = predict(origin_name=column, unit=unit, most_common_type=most_common_type, percent_70=percent_70)
    else:
        most_common_data = dict(Counter(col).most_common(3)).keys()
        similarity = predict(origin_name=column, unit=unit, most_common_type=most_common_type, most_common_data=most_common_data)
        col_info['最常见值'] = [f'{data[:4]}...' if len(str(data)) > 6 else str(data) for data in most_common_data]
    similarity = sorted(similarity, key=itemgetter(0), reverse=True)[:3]
    col_info['相似度'] = {similarity[i][1]['nameChs']: round(similarity[i][0], 2) for i in range(len(similarity))}
    col_info['确认情况'] = '无'
    return col_info


if __name__ == '__main__':
    res = {}
    datas = '/Users/har/Desktop/无锡电信.xlsx'
    df = pd.read_excel(datas).head(10)
    for column in df:
        col = df[column]
        res[column] = main(column, col, {'血脂四项:甘油三脂(TG)': '甘油三酯'})
    df = pd.DataFrame(res)
    df.T.to_excel('列信息.xlsx')