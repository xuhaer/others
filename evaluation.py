"""处理包含体检数据的excel文档"""
import json
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right

import jieba
import numpy as np
import pandas as pd

# jieba.load_userdict('st_dict.txt')

def dtype_cnt(x):
    """判断某列中某cell的数据类型"""
    if isinstance(x, str):
        return 'str'
    elif isinstance(x, (float, int)):
        if np.isnan(x):
            return 'nan'
        return 'numeric'


def col_type_cnt(df, result):
    """
    统计原始数据各列数据类型
        params: df--pd.df
        return: 以列名为key, 'numeric'、'str'、'bool'、'nan'
                的个数值构成的列表的字典
    """
    res, z = defaultdict(list), {}
    for col in df:
        cnt_dict = dict(Counter(df[col].map(dtype_cnt)))
        result[col].update({x: cnt_dict.setdefault(x, np.nan) for x in ['numeric', 'str', 'nan']})
    return result


def predict_st_names(df, result):
    """
    构建以nameChs 和 nameChsAlts 为键，name的set 为值的字典
        如:{'空腹血糖': {'GLU'}, '血糖': {'GLU'}, '白细胞': {'ULEU', 'WBC', 'stool07'} ......}
    """
    with open('/Users/har/Desktop/st_names_predict.json') as f:
        predict_map = json.load(f)

    for col in df.columns:
        likely_name = []
        # 如果col为: `一般检查-身高`, 不直接把 `一般检查-身高` 拿去分词, 后续col取 `身高`
        sub_col = col.split('-')[-1]
        if predict_map.get(sub_col):
            result[col].update({'匹配列名': predict_map[sub_col].split(',')})
        else:
            for x in jieba.cut(sub_col):
                if x in predict_map:
                    likely_name.extend(predict_map[x].split(','))
            if likely_name:
                result[col].update({'相似列名': likely_name})


def col_values_check(df, s_t, result):
    """检查df中各列对应人群的健康情况
        先决条件:
                1.df中的带检查列(col)数据类型为['int64', 'float64']
                2.df中的带检查列(col)与prc中的st有关联--存在或相似
    """
    for col in df.columns:
        if '相似列名' in result[col] or '匹配列名' in result[col]:
            flag = '相似列名' if '相似列名' in result[col] else '匹配列名'
            # 多个匹配项取第一个来预测评估
            matched_name = result[col][flag][0]
            if not matched_name in s_t.index:
                continue
            # 能到这一步，说明该col类型在prc中为float, 可强制转换
            legal_range = json.loads(s_t.loc[matched_name, :]['RefRange'])
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except ValueError:
                # This should not happen.
                pass
            if legal_range['max'] == 'Infinity':
                legal_range['max'] = 9999
            if df[col].min() < float(legal_range['min']) or \
                df[col].max() > float(legal_range['max']):
                sorted_col = np.sort(df[col].dropna())
                health_min = bisect_left(sorted_col, legal_range['min'])
                health_max = len(sorted_col) - bisect_right(sorted_col, legal_range['max'])
                result[col].update({'指标异常比例': f'约{(health_min + health_max) / len(df[col])*100:.2f}%'})
            else:
                result[col].update({'指标异常比例': '0%'})


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


def evaluation(df, s_t, output_path):
    result = defaultdict(dict)
    col_type_cnt(df, result)
    predict_st_names(df, result)
    col_values_check(df, s_t, result)

    df1 = pd.DataFrame(result)
    df = pd.concat([df1, df.describe(include='all').loc[['unique', 'top', 'freq', 'min', 'max']]], sort=False)
    # style_df = df.T.style.\
    #     applymap(highlight_illegal_data, subset=['非法数据']).\
    #     apply(highlight_illegal_max_min, attr='color: red', axis=1, subset=['合法范围', '非法数据', 'min', 'max'])
    # 染色美化跑杨子石化有点问题,可暂不染色
    # style_df.to_excel(output_path, engine='openpyxl', float_format='%.3f')
    df.T.to_excel(output_path, float_format='%.3f')



# input_df = pd.read_excel('/Users/har/Desktop/许某/2018贮运厂.xls', header=[0, 1])
# # 支持2级表头
# input_df.columns = input_df.columns.map(lambda x: '-'.join(x) if 'Unnamed' not in x[1] else x[0])
# input_df.reset_index(drop=True, inplace=True)
# input_df.drop_duplicates(inplace=True)
# input_df.to_excel('/Users/har/Desktop/许某/2018贮运厂表头合并后.xls')
input_df = pd.read_excel('/Users/har/Desktop/许某/2018质检中心_表头合并后.xls')
s_t = pd.read_excel('/Users/har/Desktop/T_SampleType.xls')
s_t.set_index('name', inplace=True)
s_t.dropna(how='all')
s_t.fillna('', inplace=True)
s_t = s_t[s_t['RefRange'] != '']
evaluation(input_df, s_t, '/Users/har/Desktop/许某/2018质检中心_表头合并后_eval.xls')
