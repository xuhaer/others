import re
import json
import time

from collections import Counter, defaultdict
from operator import itemgetter

import jieba


with open('./excel_eval/st.json') as f:
    SAMPLETYPE = json.load(f)


with open('./excel_eval/refRange.json') as f:
    REFRANGE = json.load(f)


def name_similarity(origin_name):
    '''
        给予名称相似度权重50%
        todo: 需要考虑词汇权重，比如：高密度脂蛋白、非高密度脂蛋白 仅一字之差，此函数对此无法很好的处理。
    '''
    similar_list = []
    for st in SAMPLETYPE:
        if origin_name in [st['nameChs'], st['name']]:
            sim = 0.5
        elif origin_name in [st['nameChsAlts']]:
            sim = 0.3
        else:
            st_name_str = f"{st['nameChs']} {st['name']} {st['nameChsAlts']}"
            st_name_words = set(jieba.cut(st_name_str)) - {'-', ' ', '_', ')', '('}
            origin_name_words = set(jieba.cut(origin_name)) - {'-', ' ', '_', ')', '('}
            sim = round(len(st_name_words & origin_name_words) / max(len(st_name_words), len(origin_name_words)) / 2, 2)
            origin_name_words_eng = set(re.findall(r'[a-zA-Z1-9]{2,}', origin_name))
            st_name_words_eng = set(jieba.cut(st['name'])) - {'-', ' ', '_', ')', '('}
            eng_name_sim = round(len(st_name_words_eng & origin_name_words_eng) / max(len(st_name_words_eng), len(origin_name_words_eng)) / 2, 2)
            sim += eng_name_sim
        if sim > 0:
            if sim > 0.5:
                sim = 0.5
            similar_list.append([sim, st])
    return sorted(similar_list, key=itemgetter(0), reverse=True)[:5]


def dataType_similarity(similarity, most_common_type):
    '''给予数值类型相似度权重10%'''
    if most_common_type == 'numeric':
        for index, (sim, st) in enumerate(similarity):
            if st['dataType'] in ['[float]', 'float', 'int']:
                similarity[index][0] += 0.1
    elif most_common_type == 'str':
        for index, (sim, st) in enumerate(similarity):
            if st['dataType'] == 'text':
                similarity[index][0] += 0.1
    else:
        pass
    return similarity

def counter_divide(counter):
    numeric_cnter, str_cnter, sample_type = {}, {}, defaultdict(int)
    for v, cnt in counter.items():
        try:
            numeric_v = float(v)
        except ValueError:
            str_cnter[v] = cnt
            sample_type['str'] += cnt
        else:
            if v:
                numeric_cnter[numeric_v] = cnt
                sample_type['numeric'] += cnt
            else: # 可能为"" 空字符？？
                sample_type['nan'] += cnt
    return numeric_cnter, str_cnter, sample_type


def data_similarity(name_similarity, counter, col_info):
    '''传入值的Counter 返回相似度，给予值的范围相似度权重40%'''

    likely_name = []
    numeric_cnter, str_cnter, sample_type = counter_divide(counter)
    # 值的类型判断
    col_info['value_type'] = dict(sample_type)
    v_most_common_type = max(zip(sample_type.values(), sample_type.keys()))[1]
    similarity = dataType_similarity(name_similarity, v_most_common_type)

    # 值的判断
    numeric_counter = Counter(numeric_cnter) # filter
    total_values = sum(counter.values())
    numeric_percent = col_info['value_type'].get('numeric', 0) / (col_info['value_type'].get('str', 1) + col_info['value_type'].get('numeric', 0))
    col_info['most_common_20_values'] = str(dict(counter.most_common(20)))
    if v_most_common_type == 'numeric' or numeric_percent > 0.3:
        col_info['max'] = max(numeric_cnter)
        col_info['min'] = min(numeric_cnter)
        col_info['invalid_values'] = str_cnter
        for index, (sim, st) in enumerate(similarity):
            legal_percent = 0
            allow_min, allow_max = REFRANGE.get(st['name'], [-999, 999])
            if REFRANGE.get(st['name']):
                for v in sorted(numeric_counter.keys(), reverse=True):
                    if allow_min <= v <= allow_max:
                        factor = 0.4
                        valid_percent = numeric_counter[v] / total_values
                        legal_percent += valid_percent
                        similarity[index][0] += factor * valid_percent
            else:
                similarity[index][0] += 0.2
            likely_name.append({
                'name': st['name'],
                'nameChs': st['nameChs'],
                'dataType': st['dataType'],
                'RefRange': st['defaultRefRange'],
                'unit': st['unit'],
                'valid_percent': round(legal_percent, 2),
                'similarity': 0.99 if round(similarity[index][0], 2) > 1 else round(similarity[index][0], 2)
            })
        col_info['function'] = "to_float"
    else:
        col_info['function'] = "to_str"

    sim = sorted(similarity, key=itemgetter(0), reverse=True)[:3]
    col_info['std_name'] = {'name': None, 'nameChs': None}
    if likely_name:
        col_info['likely_name'] = sorted(likely_name, key=itemgetter('similarity'), reverse=True)[:3]
    elif sim:
        col_info['likely_name'] = [s[1] for s in sim]
    if sim:
        if sim[0][0] > 0.5:
            col_info['std_name'] = {'name': sim[0][1]['name'], 'nameChs': sim[0][1]['nameChs']}
    return sim

def make_predict(all_data, sep='@_@'):
    res = []
    i = 0
    for k, v in all_data.items():
        col_info = {}
        group_name, item_name = k.split(sep)
        col_info['group_name'] = group_name
        col_info['item_name'] = item_name
        name_sim = name_similarity(item_name)
        data_similarity(name_sim, Counter(v), col_info)
        i += 1
        res.append(col_info)
        time.sleep(0.1)
    with open('预测结果.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


with open('oringin_data_counter.json') as f:
    all_data = json.load(f)
    make_predict(all_data)
