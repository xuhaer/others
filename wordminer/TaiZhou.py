'''
    将.docx文档中的表格数据提取成Pandas的DataFrame
    用于中行体检报告数据（泰州第二人民医院）
'''
import os
import re
import json
import glob

import pandas as pd

from docx.api import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph


def table_to_df(table):
    keys = None
    data = []

    for i, row in enumerate(table.rows):
        text = (cell.text for cell in row.cells)
        if i == 0:
            keys = tuple(text)
            continue
        row_data = dict(zip(keys, text))
        data.append(row_data)
    df = pd.DataFrame(data)
    return df


def iter_block_items(document):
    document_elm = document.element.body
    for child in document_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def extract_document_data(document):
    '''从Document中提取表格数据并保留其表头信息'''
    samples = []
    global table_header

    for block in iter_block_items(document):
        # 表头信息保留，表尾信息舍弃，表格数据的上一个值为有效的表头信息
        if isinstance(block, Paragraph):
            t_header = block.text
            if t_header != '\n':
                table_header = t_header
        elif isinstance(block, Table):
            table_df = table_to_df(block)
            if not table_df.empty:
                for v in table_df.values:
                    samples.append({table_header: dict(zip(table_df.columns, v))})
    return samples


def get_summary(doc):
    '''生成summary数据, 对于泰州第二人民医院, 该数据为doc.tables[-3:]中的段落字段'''
    for table in list(doc.tables)[-3:]:
        summary = ''
        for row in table.rows:
            for cell in row.cells:
                summary += cell.text
        if '结论及建议' in summary:
            # 仅要症状，不要建议，均为: '1、[高血压]' 这样的标示
            summary = '\n'.join(re.findall(r'(\d+、\[.*\])', summary))
            return f'结论及建议:\n{summary}'
    else:
        raise ValueError('无有效的总检结论数据！')


def get_basic_info(doc, file_name):
    '''生成basic_info数据, 对于泰州第二人民医院, 该数据为doc.paragraphs中最前面'''
    basic_info = {}
    file_name = os.path.splitext(file_name)[0]
    if '_' not in file_name:
        return basic_info
    name = file_name.split('_')[1]
    basic_info['name'] = name
    for para in doc.paragraphs[:30]:
        line = para.text.strip()
        # todo, 改为正则匹配更靠谱
        if len(line) == 18:
            basic_info['身份证'] = line
        elif len(line) == 10 and '-' in line:
            if '出生日期' in basic_info:
                basic_info['体检日期'] = line
            else:
                basic_info['出生日期'] = line
        elif '男' in line or '女' in line:
            basic_info['性别'] = line
    return basic_info


def get_raw_data(docx_paths):
    '''生成所有docx文件有效数据的集合'''
    raw_data = []
    for docx_path in docx_paths:
        document = Document(docx_path)
        samples = extract_document_data(document)
        summary = get_summary(document)
        basic_info = get_basic_info(document, os.path.basename(docx_path))
        raw_data.append({
            'file_name': os.path.basename(docx_path),
            'basic_info': basic_info,
            'summary': summary,
            'samples': samples
        })
    return raw_data


def generate_standard_data(raw_data):
    '''将raw_data标准化为更方便入库的格式数据'''
    standard_datas = []
    for data in raw_data:
        standard_data, std_samples = {}, []
        standard_data['file_name'] = data['file_name']
        standard_data['basic_info'] = data['basic_info']
        standard_data['summary'] = data['summary']
        for group_samples in data['samples']:
            for group_name, group_sample in group_samples.items():
                try:
                    std_samples.append({
                        "group_name": group_name,
                        "item_name": group_sample['项目名称'],
                        "value": group_sample.get('检查结果', group_sample.get('结果')),
                        "refrange": group_sample.get('参考值')
                    })
                except KeyError as e:
                    print(e)
            standard_data['samples'] = std_samples
        standard_datas.append(standard_data)
    return standard_datas


docx_paths = glob.glob('～/Desktop/泰州市第二人民医院144-个人docx/*.docx')
raw_data = get_raw_data(docx_paths)
standard_datas = generate_standard_data(raw_data)

with open('～/Desktop/泰州市144.json', 'w') as f:
    json.dump(standard_datas, f, ensure_ascii=False, indent=2)
