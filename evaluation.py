"""处理包含体检数据的excel文档"""
import json
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right

import jieba
import numpy as np
import pandas as pd


def dtype_cnt(x):
    """判断某列中某cell的数据类型"""
    if isinstance(x, str):
        return 'str'
    elif isinstance(x, (float, int)):
        if np.isnan(x):
            return 'nan'
        return 'numeric'


def col_type_cnt(data):
    """
    统计原始数据各列数据类型
        params: data--pd.df
        return: 以列名为key, 'numeric'、'str'、'bool'、'nan'
                的个数值构成的列表的字典
    """
    res, z = defaultdict(list), {}
    result = defaultdict(dict)
    for col in data:
        cnt_dict = dict(Counter(data[col].map(dtype_cnt)))
        result[col].update({x: cnt_dict.setdefault(x, np.nan) for x in ['numeric', 'str', 'nan']})
    return result


def gen_st_names(s_t):
    """
    构建以nameChs 和 nameChsAlts 为键，name的set 为值的字典
        如:{'空腹血糖': {'GLU'}, '血糖': {'GLU'}, '白细胞': {'ULEU', 'WBC', 'stool07'} ......}
    """
    st_names = defaultdict(set)
    for row in s_t.loc[ :, ['name', 'nameChs', 'nameChsAlts']].fillna('').values:
        st_names[row[1]].add(f'{row[0]}')
        if  ',' in row[2]:
            for nameChsAlts in row[2].split(','):
                st_names[nameChsAlts].add(f'{row[0]}')
        elif row[2] and row[2] != ' ':
            st_names[row[2]].add(f'{row[0]}')
    return st_names


def col_values_check(data, st_names, s_t, result):
    """检查data中各列数据的合法性
        先决条件:
                1.data中的带检查列(col)数据类型为['int64', 'float64']
                2.data中的带检查列(col)与prc中的st有关联--存在或相似
    """
    legal_cols = set()
    for col in data.columns:
        likely_name = set()
        if st_names.get(col):
            result[col].update({'对应prc列名': ','.join(st_names[col])})
        for x in jieba.cut(col):
            if x in st_names:
                likely_name.update(st_names[x])
        if likely_name:
            result[col].update({'可能列名': ','.join(likely_name)})
        # 数据检测
        if '可能列名' in result[col] or '对应prc列名' in result[col]:
            flag = '可能列名' if '可能列名' in result[col] else '对应prc列名'
            for like_name in result[col][flag].split(','):
                the_row = s_t[s_t['name'] == like_name].loc[:, ['nameChs', 'nameChsAlts', 'dataType', 'defaultRefRange', 'unit']].fillna('').to_dict(orient='records')
                # the row 肯定不为空
                the_row = the_row[0]
                the_range = json.loads(the_row['defaultRefRange'])
                the_type = the_row['dataType']
                if data[col].dtypes in ['int64', 'float64'] \
                    and the_range and the_type in ['int', 'float', '[float]']:
                    if isinstance(the_range, dict):
                        legal_range = {}
                        for v in the_range.values():
                            if isinstance(v, dict):
                                for v in v.values():
                                    if legal_range.setdefault('min', v[0]) > v[0]:
                                        legal_range['min'] = v[0]
                                    if legal_range.setdefault('max', v[1]) < v[1]:
                                        legal_range['max'] = v[1]
                            else:
                                if legal_range.setdefault('min', v[0]) > v[0]:
                                    legal_range['min'] = v[0]
                                if legal_range.setdefault('max', v[1]) < v[1]:
                                    legal_range['max'] = v[1]
                    elif isinstance(the_range, list):
                        legal_range = {'min': the_range[0], 'max': the_range[1]}
                    # legal_range为prc中defaultRange允许的最大范围
                    if data[col].min() < float(legal_range['min']) or \
                        data[col].max() > float(legal_range['max']):
                        sorted_col = np.sort(data[col].dropna())
                        illegal_min = bisect_left(sorted_col, legal_range['min'])
                        illegal_max = len(sorted_col) - bisect_right(sorted_col, legal_range['max'])
                        (illegal_min + illegal_max) / len(data[col])
                        result[col].update({'非法数据': f'约{(illegal_min + illegal_max) / len(data[col])*100:.2f}%', '合法范围': [legal_range['min'], legal_range['max']]})
                    else:
                        result[col].update({'非法数据': '0%', '合法范围': [legal_range['min'], legal_range['max']]})


def highlight_max_data(data, attr):
    if data.ndim == 1:
        is_max = data == data.max()
        return [attr if v else '' for v in is_max]
    else:  # from .apply(axis=None)
        is_max = data == data.max().max()
        return pd.DataFrame(np.where(is_max, attr, ''),
                            index=data.index, columns=data.columns)


def highlight_illegal_data(data):
    if isinstance(data, str):
        if '约' in data:
            return 'color: red'
        elif data == '0%':
            return 'color: green'
    else:
        return ''


def highlight_illegal_max_min(data, attr):
    illegal = [False, False, False, False]
    if '约' in str(data['非法数据']):
        if data['min'] < data['合法范围'][0] or data['min'] > data['合法范围'][1]:
            illegal[2] = True
        if data['max'] > data['合法范围'][1] or data['max'] < data['合法范围'][0]:
            illegal[3] = True
    return [attr if v else '' for v in illegal]


def evaluation(data, s_t, output_path='/Users/har/Desktop/安徽电信2018数据/evaluation.xls'):
    st_names = gen_st_names(s_t)
    evaluation = col_type_cnt(data)
    col_values_check(data, st_names, s_t, evaluation)
    df1 = pd.DataFrame(evaluation)
    df = pd.concat([df1, data.describe(include='all').loc[['unique', 'top', 'freq', 'min', 'max']]], sort=False)
    style_df = df.T.style.\
        applymap(highlight_illegal_data, subset=['非法数据']).\
        apply(highlight_illegal_max_min, attr='color: red', axis=1, subset=['合法范围', '非法数据', 'min', 'max'])

    style_df.to_excel(output_path, engine='openpyxl', float_format='%.3f')

merged = pd.read_excel('/Users/har/Desktop/安徽电信2018数据/merged.xls')
s_t = pd.read_csv('/Users/har/Desktop/安徽电信2018数据/T_SampleType_201811121655.csv')
evaluation(merged, s_t, '/Users/har/Desktop/安徽电信2018数据/evaluation_1.xls')
