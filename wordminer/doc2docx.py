'''
    用于批量将.doc 文件转为 .docx 文件，只能用于windows环境
    pip install pypiwin32
'''
import os
import glob

from win32com import client as wc


def get_doc_file_names(dir_path):
    '''遍历给定path路径下(包括子文件夹中)的所有.doc文件，并返回文件绝对路径集合的一个列表'''
    # 用 glob.glob 的 ** 更简洁
    return glob.glob(f'{dir_path}/**/*.doc', recursive=True)
    # file_paths = []
    # dirlist = os.walk(dir_path)
    # for root, dirs, files in dirlist:
    #     for f in files:
    #         if f.endswith('.doc'):
    #             # print(os.path.join(root, f))
    #             file_paths.append(os.path.join(root, f))
    # return file_paths


def doc_to_docx(file_paths):
    word = wc.Dispatch('Word.Application')
    for file_path in file_paths:
        doc = word.Documents.Open(file_path)
        # doc.SaveAs 另存为后缀为".docx"的文件，其中参数12指docx文件
        doc.SaveAs(os.path.join("D:/test/data/docx", os.path.basename(file_path) + "x"), 12)
        doc.Close()
    word.Quit()


dir_path = "D:/test/data/doc/"
file_paths = get_doc_file_names(dir_path)
doc_to_docx(file_paths)
