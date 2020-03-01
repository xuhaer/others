'''pip install pypiwin32, 只能在windows环境下'''

import os
from win32com import client as wc


def get_doc_file_names(path):
    '''遍历给定path路径下的所有.doc文件，并返回文件绝对路径集合的一个列表'''
    file_paths = []
    dirlist = os.walk(path)
    for root, dirs, files in dirlist:
        for f in files:
            if f.endswith('.doc'):
                # print(os.path.join(root, f))
                file_paths.append(os.path.join(root, f))
    return file_paths


def doc_to_docx(file_paths):
    word = wc.Dispatch('Word.Application')
    for file_path in file_paths:
        doc = word.Documents.Open(file_path)
        doc.SaveAs(os.path.join("D:/test/data/docx", os.path.basename(file_path) + "x"), 12) # 另存为后缀为".docx"的文件，其中参数12指docx文件
        doc.Close()
    word.Quit()


path = "D:/test/data/doc/"
file_paths = get_doc_file_names(path)
doc_to_docx(file_paths)
