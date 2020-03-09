import os
import re
import json

from collections import Counter, defaultdict
from operator import itemgetter

from nltk.util import ngrams

# from get_samples_data import get_SampleType
from samples_value_counter import connect_db, samples_value_counter


NGRAM = 2
HERE = os.path.dirname(__file__)


def jaccard_distance(a, b):
    """Calculate the jaccard distance between sets A and B"""
    if not a or not b:
        return 0
    a = set(a)
    b = set(b)
    return 1.0 * len(a&b) / len(a|b)


def get_name_ngrams(name):
    """返回item_name 或 group_item 的ngrams"""
    ng = []
    if not name:
        return None
    for name in name.split(','):
        valid_name = re.sub(r'[-_() 、\[\]（）]', '', name).lower()
        ng.extend(list(ngrams(list(valid_name), NGRAM)))
    return ng


def name_divide(item_name):
    '''
        将item_name切分为中文名和英文名，以下面sep为分隔符，如：
            糖类抗原CA-50 -> ['糖类抗原CA-50', None]
            神经原特异性烯醇化酶(NSE) -> ['神经原特异性烯醇化酶', 'NSE']
            其中英文名均在以下的括号里，且由字母、数字、-、_、/、%、#以及几个希腊字母组成
    '''
    sep_list = ['()', '（）', '[]', '【】', '(）', '（)']
    if not item_name:
        return None, None
    if any(len(set(item_name) & set(sep)) == 2 for sep in sep_list):
        chs_name_matches = re.findall(r'(.*?)[\(（\[【]', item_name)
        eng_name_matches = re.findall(r'[\(（\[【]([a-zA-Z0-9\-\/%#_αβγ]*)[\)）\]】Ⅰ]', item_name)
        chs_name = chs_name_matches[0] if eng_name_matches else None
        chs_name = chs_name if chs_name else item_name
        eng_name = eng_name_matches[0] if eng_name_matches else None
    else:
        chs_name, eng_name = item_name, None
    return chs_name, eng_name


def calculate_ref_range(RefRange):
    '''
        简化SampleType中复杂的defaultRefRange，对于值为字典类型，递归调用
            ['阴性'] --> [9999, -9999]
            [3.9,5.6] --> [3.9,5.6]
            {'male': [40, 'Infinity'], 'female': {'age20-49': [35, 100], 'age>50': [50, 135]}} --> [35, 9999]、
    '''
    if isinstance(RefRange, list):
        if len(RefRange) != 2:
            return [9999, -9999]
        min_v = float(RefRange[0])
        max_v = float(RefRange[1])
        return [min_v, max_v]
    elif isinstance(RefRange, dict):
        min_v_list, max_v_list = [], []
        for v in RefRange.values():
            temp_min_v, temp_max_v = calculate_ref_range(v)
            min_v_list.append(temp_min_v)
            max_v_list.append(temp_max_v)
        return [min(min_v_list), max(max_v_list)]
    else:
        raise ValueError(f'未知的defaultRefRange: {RefRange}!')


def make_st_with_ngrams(pyodbc_url):
    '''一次性返回所有附带ngrams信息的SampleType'''
    SampleTypeWithNgrams = {}
    # SAMPLETYPE = get_SampleType(pyodbc_url)
    with open(os.path.join(HERE, 'data/st.json')) as f:
        #todo: calculate from SAMPLETYPE
        SAMPLETYPE = json.load(f)
    for s in SAMPLETYPE:
        SampleTypeWithNgrams[s['name']] = {
            'SampleType': s,
            'name_ngrams': get_name_ngrams(s['name']),
            'nameAlts_ngrams': get_name_ngrams(s['nameAlts']),
            'nameChs_ngrams': get_name_ngrams(s['nameChs']),
            'nameChsAlts_ngrams': get_name_ngrams(s['nameChsAlts']),
        }
    return SampleTypeWithNgrams


def predict_likely_st_based_on_name(group_name, item_name):
    '''
        预测给定的group_name, item_name对应的SampleType
        返回有序(按可能性排序)的列表，例如给定group_name='身高、体重检查', item_name='身高'，返回:
            [
                {'name': 'height', 'nameChs': '身高', '相似度': 0.5},
                {'name': 'weight', 'nameChs': '体重', '相似度': 0.1},
            ]
        跑了1729个人工确认过的配置规则，该函数的正确率为 74.7%
    '''
    likely_st_list = []
    group_name_ngrams = get_name_ngrams(group_name)
    chs_name, eng_name = name_divide(item_name)
    chs_name_ngrams = get_name_ngrams(chs_name)
    eng_name_ngrams = get_name_ngrams(eng_name)
    for st_name, st_detail in SampleTypeWithNgrams.items():
        SampleType = st_detail['SampleType']
        group_sim = jaccard_distance(st_detail['nameChs_ngrams'], group_name_ngrams)
        nameChs_sim = jaccard_distance(st_detail['nameChs_ngrams'], chs_name_ngrams)
        nameChsAlts_sim = jaccard_distance(st_detail['nameChsAlts_ngrams'], chs_name_ngrams)
        sim = round(group_sim * 0.2 + nameChs_sim * 0.5 + nameChsAlts_sim * 0.3, 4)
        if eng_name_ngrams:
            name_sim = jaccard_distance(st_detail['name_ngrams'], eng_name_ngrams)
            nameAlts_sim = jaccard_distance(st_detail['nameAlts_ngrams'], eng_name_ngrams)
            sim += round(name_sim * 0.5 + nameAlts_sim * 0.5, 4)
        if sim:
            likely_st_list.append({
                '相似度': sim,
                'nameChs': SampleType['nameChs'],
                'name': st_name,
                'dataType': SampleType['dataType'],
                'ref_range': calculate_ref_range(json.loads(SampleType['defaultRefRange'])),
                'unit': SampleType['unit'],
            })
    return sorted(likely_st_list, key=itemgetter('相似度'), reverse=True)[:10]


def values_cnt_divide(values_cnt):
    '''
        统计某检查项的值的类型及其数量
            例如：身高数据values_cnt：{'168': 20, '178': 30, '弃检': 3}
                返回其统计值和数值部分已经非法数据：
                {'numeric': 50, 'str': 3}, {168: 20, 178: 30}, {'弃检': 3}
    '''
    values_type_cnt = {'numeric': 0, 'str': 0}
    numeric_values_cnt, invalid_values = {}, defaultdict(int)
    for v, cnt in values_cnt.items():
        try:
            numeric_v = float(v)
        except ValueError:
            values_type_cnt['str'] += cnt
            invalid_values[v] += cnt
        else:
            values_type_cnt['numeric'] += cnt
            numeric_values_cnt[numeric_v] = cnt
    return values_type_cnt, numeric_values_cnt, invalid_values


def correct_likely_st_based_on_values(values_cnt, likely_st_list):
    '''根据体检结果的值汇总数据来修正仅仅根据名称预测的likely_st_list结果'''
    values_type_cnt, numeric_values_cnt, invalid_values = values_cnt_divide(values_cnt)
    values_type = 'numeric' if values_type_cnt['numeric'] > values_type_cnt['str'] else 'str'
    for likely_st in likely_st_list:
        valid_values_cnt = 0
        ref_range = likely_st['ref_range']
        data_type = likely_st['dataType']
        if data_type in ['float', 'int'] and values_type == 'numeric':
            likely_st['相似度'] += 0.1
        if data_type == 'text' and values_type == 'str':
            likely_st['相似度'] += 0.1
        for v, cnt in numeric_values_cnt.items():
            if ref_range[0] <= v <= ref_range[1]:
                valid_values_cnt += cnt
        likely_st['相似度'] += valid_values_cnt / sum(values_type_cnt.values()) * 0.15
    most_likely_st_list = sorted(likely_st_list, key=itemgetter('相似度'), reverse=True)[:3]
    for st in most_likely_st_list:
        del st['相似度']
        del st['ref_range']
        del st['unit']
    return most_likely_st_list


def make_predict(origin_data, all_matched_rules):
    '''预测体检数据对应的SampleType，并依据人工确认过的匹配规则返回预测值'''
    predict_res = []
    for k, values_cnt in origin_data.items():
        group_name, item_name = re.findall(r'group_name: (.*), item_name:(.*)', k)[0]
        values_type_cnt, numeric_values_cnt, invalid_values = values_cnt_divide(values_cnt)
        # 根据group_name和item_name做全匹配筛选，若命中，
        # 则不进行相应的预测，直接返回匹配好的配置规则
        has_matched_rule = list(filter(lambda rule: rule['group_name'] == group_name and rule['item_name'] == item_name, all_matched_rules))
        if has_matched_rule:
            std_name = has_matched_rule[0]['std_name']
            likely_st = '命中以往已配置规则'
        else:
            likely_st = predict_likely_st_based_on_name(group_name, item_name)
            likely_st = correct_likely_st_based_on_values(values_cnt, likely_st)
            # std_name = {'name': likely_st[0]['name'], 'nameChs': likely_st['nameChs']}
            if likely_st:
                std_name = {'name': likely_st[0]['name'], 'nameChs': likely_st[0]['nameChs']}
            else:
                std_name = {'name': None, 'nameChs': None}
        data_type = max([[v, k] for k, v in values_type_cnt.items()])[1]
        predict_st = {
            'group_name': group_name,
            'item_name': item_name,
            'values_type_cnt': values_type_cnt,
            'most_common_10_values': str(dict(Counter(values_cnt).most_common(10))),
            'function': 'to_float' if data_type == 'numeric' else 'to_str',
            'std_name': std_name,
            'likely_name': likely_st,
        }
        if data_type == 'numeric' and invalid_values:
            predict_st['invalid_values'] = invalid_values
        predict_res.append(predict_st)
    return predict_res


if __name__ == "__main__":
    hospital = '爱康国宾'
    mongo_db_url = os.environ.get('Mongo_DB')
    pyodbc_url = os.environ.get('PDATA_DB')
    collection = connect_db(mongo_db_url, 'test', 'boc_appointment')

    the_collection = collection.find({'hospital': hospital})
    origin_data = samples_value_counter(the_collection)
    SampleTypeWithNgrams = make_st_with_ngrams(pyodbc_url)

    with open(os.path.join(HERE, 'data/matched_rules.json')) as f:
        all_matched_rules = json.load(f)
    predict_res = make_predict(origin_data, all_matched_rules)
    with open(os.path.join(HERE, f'data/{hospital}预测配置结果.json'), 'w') as f:
        json.dump(predict_res, f, ensure_ascii=False, indent=2)
