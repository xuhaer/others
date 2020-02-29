'''
    将.docx文档中的表格数据提取成Pandas的DataFrame
    缺陷是没法判断紧邻表格前的表格说明信息
'''
import pandas as pd
from docx.api import Document

def table_to_df(table):
    '''用于中行体检报告数据（泰州第二人民医院）'''
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

document = Document('/Users/har/Desktop/19093517_徐文娟.docx')
for table in document.tables:
    df = table_to_df(table)
    print(df)
    print()
