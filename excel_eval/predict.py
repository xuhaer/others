import re
import json
import time

from collections import Counter, defaultdict
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
        if origin_name in [st['nameChs'], st['name'], st['nameChsAlts']]:
            sim = 1
        else:
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
    # if most_common_type:
    #     similarity = dataType_similarity(similarity, most_common_type)
    # if most_common_data:
    #     similarity = most_common_data_similarity(similarity, most_common_data)
    # if unit:
    #     similarity = unit_similarity(similarity, unit)
    # if percent_70:
    #     similarity = data_value_similarity(similarity, percent_70)
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


def before_predict(column_name, col, col_info, unit):
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
        similarity = predict(origin_name=column_name, unit=unit, most_common_type=most_common_type, percent_70=percent_70)
    else:
        most_common_data = dict(Counter(col).most_common(3)).keys()
        similarity = predict(origin_name=column_name, unit=unit, most_common_type=most_common_type, most_common_data=most_common_data)
        col_info['最常见值'] = [f'{data[:4]}...' if len(str(data)) > 6 else str(data) for data in most_common_data]
    return similarity


def main(column_name, col, confirmed_st=None, unit=None):
    col_info = {}
    if confirmed_st and column_name in confirmed_st:
        col_info['匹配列'] = confirmed_st[column_name]
        col_info['确认情况'] = '已确认'
        st = [st for st in SAMPLETYPE if st['nameChs'] == col_info['匹配列']]
        # assert len(st) == 1
        col_info['标准单位'] = st[0]['unit']
        col_info['参考范围'] = REFRANGE.get(st[0]['name'])

    similarity = before_predict(column_name, col, col_info, unit)
    similarity = sorted(similarity, key=itemgetter(0), reverse=True)[:3]
    col_info['可能列'] = [sim[1]['nameChs'] for sim in similarity[1:]]
    col_info.setdefault('标准单位', similarity[0][1]['unit'] if similarity else None)
    col_info.setdefault('参考范围', REFRANGE.get(similarity[0][1]['name']) if similarity else None)
    if col_info.get('70%的值分布于') and col_info.get('参考范围'):
        v_70_min, v_70_max = col_info['70%的值分布于']
        refRange_min, refRange_max = col_info['参考范围']
        is_value_ideal = v_70_min >= refRange_min and v_70_max <= refRange_max
        col_info['70%分布值是否正常'] = True if is_value_ideal else False
    col_info.setdefault('匹配列', similarity[0][1]['nameChs'] if similarity else None)
    col_info.setdefault('确认情况', '无')
    return col_info


def highlight_mixedtype_data(data):
    """对str、nan、与numeric 的混合类型列染色"""
    return 'color: red' if len(data) >= 3 else ''


def highlight_unnormal_col(data):
    """对70%分布值是否正常列染色"""
    return 'color: red' if not data else 'color: green'


def make_confirmed_json(confirmed_st):
    confirmed_excel = pd.read_excel('confirmed.xlsx', index_col=0)
    relations = zip(confirmed_excel.index, confirmed_excel['匹配列'], confirmed_excel['确认情况'])
    map_relation = {k: v for k, v, is_confirmed in relations if is_confirmed == '已确认'}
    if map_relation:
        confirmed_st.update(map_relation)
        with open('./excel_eval/temp_confirmed_st.json', 'w') as f:
            json.dump(confirmed_st, f, ensure_ascii=False, indent=4)


def data_similarity(name_similarity, counter, col_info):
    '''传入值的Counter 返回相似度'''
    sample_type = defaultdict(int)
    numeric_cnter = {}
    for v, cnt in counter.items():
        try:
            numeric_v = float(v)
        except ValueError:
            sample_type['str'] += cnt
        else:
            if v:
                numeric_cnter[numeric_v] = cnt
                sample_type['numeric'] += cnt
            else: # 可能为"" 空字符？？
                sample_type['nan'] += cnt
    # 值的类型判断
    col_info['value_type'] = dict(sample_type)
    v_most_common_type = max(zip(sample_type.values(), sample_type.keys()))[1]
    similarity = dataType_similarity(name_similarity, v_most_common_type)

    # 值的判断
    numeric_counter = Counter(numeric_cnter)
    if v_most_common_type == 'numeric':
        col_info['最大值'] = max(numeric_cnter)
        col_info['最小值'] = min(numeric_cnter)
        for index, (sim, st) in enumerate(similarity):
            allow_min, allow_max = REFRANGE.get(st['name'], [-999, 999])
            for v in sorted(numeric_counter.keys(), reverse=True):
                if allow_min < v < allow_max:
                    factor = 0.5 if allow_max != 999 else 0.2
                    valid_percent = (numeric_counter[v] / sum(counter.values()))
                    similarity[index][0] += factor * valid_percent
    sim = sorted(similarity, key=itemgetter(0), reverse=True)[:3]
    if v_most_common_type == 'numeric' and sim:
        col_info['合法值比例'] = 0
        allow_min, allow_max = REFRANGE.get(sim[0][1]['name'], [-999, 999])
        for v in sorted(numeric_counter.keys(), reverse=True):
            if allow_min < v < allow_max:
                valid_percent = (numeric_counter[v] / sum(counter.values()))
                col_info['合法值比例'] += valid_percent
    return sim

def make_predict(all_data, sep='@_@'):
    res = []
    i = 0
    for k, v in all_data.items():
        col_info = {}
        group_name, item_name = k.split(sep)
        name_sim = name_similarity(item_name)
        similarity = data_similarity(name_sim, Counter(v), col_info)
        col_info['group_name'] = group_name
        col_info['item_name'] = item_name
        col_info['可能列'] = [sim[1]['nameChs'] for sim in similarity[0:]]
        col_info.setdefault('标准单位', similarity[0][1]['unit'] if similarity else None)
        col_info.setdefault('参考范围', REFRANGE.get(similarity[0][1]['name']) if similarity else None)
        # {'group_name': '一般情况', 'item_name': '身高', '参考范围': None, '可能列': ['身高'], '标准单位': 'cm'}
        i += 1
        res.append(col_info)
        time.sleep(0.4)
        # if i > 20:
        #     break
    with open('res.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

with open('all_data1.json') as f:
    all_data = json.load(f)
    make_predict(all_data)
