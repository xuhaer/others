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
