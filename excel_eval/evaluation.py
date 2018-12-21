"""处理包含体检数据的excel文档"""
import json
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right

import jieba
import numpy as np
import pandas as pd

# jieba.load_userdict('./match_dict.txt.txt')


def col_type(x):
    """判断某列中某cell的数据类型"""
    if isinstance(x, str):
        return 'str'
    elif isinstance(x, (float, int)):
        return 'nan' if np.isnan(x) else 'numeric'



def col_type_cnt(df, result):
    """
    统计原始数据各列数据类型的汇总情况
    """
    res, z = defaultdict(list), {}
    for col in df:
        cnt_dict = dict(Counter(df[col].map(col_type)))
        result[col].update({x: cnt_dict.setdefault(x, np.nan) for x in ['numeric', 'str', 'nan']})
    return result


def predict_st_names(df, result):
    """
    以json文件为中间件来预测df中各列对应prc库中可能st_name
    """
    with open('./predict_map.json') as f:
        predict_map = json.load(f)

    for col in df.columns:
        likely_name = []
        # 默认col为联级列名
        # 如果col为: `一般检查-身高`, 不直接把 `一般检查-身高` 拿去分词, 后续col取 `身高`
        sub_col = col.split('-')[-1]
        if predict_map.get(sub_col):
            result[col].update({'匹配列名': predict_map[sub_col]})
        else:
            for x in jieba.cut(sub_col):
                if x in predict_map:
                    likely_name.extend(predict_map[x].split(','))
            if likely_name:
                result[col].update({'相似列名': ','.join(likely_name)})


def col_values_check(df, result):
    """检查df中各列指标是否异常(不在defaultRefRange的区间内即异常)
        先决条件:
                1.df中的带检查列(col)与prc中的st有关联--存在或相似
                2.col匹配的 matched_name 的dataType 为 int or float
    """
    with open('./refRange.json') as f:
        s_t = json.load(f)
    for col in df.columns:
        if '相似列名' in result[col] or '匹配列名' in result[col]:
            flag = '相似列名' if '相似列名' in result[col] else '匹配列名'
            # 多个匹配项取第一个来预测评估，因此json文件有多匹配的也需按概率大小排序。
            matched_name = result[col][flag].split(',')[0]
            if not matched_name in s_t.keys():
                continue
            # 能到这一步，说明该col类型在prc中为float, 可用 `errors='coerce'` 转换
            legal_range = s_t[matched_name]
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].min() < float(legal_range[0]) or \
                df[col].max() > float(legal_range[1]):
                sorted_col = np.sort(df[col].dropna())
                health_min = bisect_left(sorted_col, legal_range[0])
                health_max = len(sorted_col) - bisect_right(sorted_col, legal_range[1])
                result[col].update({'指标异常比例': f'{(health_min + health_max) / len(df[col])*100:.2f}%'})
            else:
                result[col].update({'指标异常比例': '0%'})


def highlight_mixedtype_data(data):
    """若该列既有str类型，又有numeric 类型则输出为红色"""
    if data.isnull().values.any():
        return ['', '']
    return ['color: red', 'color: red']
    # if data.ndim == 1:
    #     is_max = data == data.max()
    #     return [attr if v else '' for v in is_max]
    # else:  # from .apply(axis=None)
    #     is_max = data == data.max().max()
    #     return pd.DataFrame(np.where(is_max, attr, ''),
    #                         index=data.index, columns=data.columns)


def highlight_unnormal_col(data):
    '该列指标异常值百分比大于30%返回红色cell'
    if isinstance(data, str):
        return 'color: red' if float(data.replace('%', '')) >= 30 else 'color: green'
    else:
        return ''


def main(input_path, output_path, header=[0]):
    if header != [0]:
        input_df = pd.read_excel(input_path, header=header)
        input_df.columns = input_df.columns.map(lambda x: '-'.join(x) if 'Unnamed' not in x[1] else x[0])
        input_df.reset_index(drop=True, inplace=True)
        input_df.drop_duplicates(inplace=True)
    else:
        input_df = pd.read_excel(input_path)
    result = defaultdict(dict)
    col_type_cnt(input_df, result)
    predict_st_names(input_df, result)
    col_values_check(input_df, result)

    output_df = pd.concat([pd.DataFrame(result), input_df.describe(include='all').loc[['unique', 'top', 'freq', 'min', 'max']]], sort=False).T
    output_df = output_df[['nan', 'numeric', 'str', '匹配列名', '相似列名', '指标异常比例', 'min', 'max', 'unique', 'top', 'freq']]
    try:
        style_df = output_df.style.\
            applymap(highlight_unnormal_col, subset=['指标异常比例']).\
            apply(highlight_mixedtype_data, axis=1, subset=['numeric', 'str'])
        style_df.to_excel(output_path, engine='openpyxl', float_format='%.3f')
    except AttributeError as e:
        print(f'染色失败: {e}, 已通过不染色方式输出.')
        output_df.to_excel(output_path, float_format='%.3f')


if __name__ == '__main__':
    input_path = '/Users/har/Desktop/许某/2018质检中心_表头合并后.xls'
    output_path = '/Users/har/Desktop/许某/2018质检中心_表头合并后_eval.xls'
    main(input_path, output_path, header=[0])
