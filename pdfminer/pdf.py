"""Use pdfminer to extract textbox rows from PDF"""
import json
import time
import glob
from pprint import pprint

import arrow

from pdfminer.layout import LAParams, LTExpandableContainer
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.layout import LTTextBoxHorizontal


def get_pages(fn, laparams):
    """打开并解析pdf，返回各页布局分析后的elements"""
    rsrcmgr = PDFResourceManager()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    with open(fn, 'rb') as fp:
        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)
            layout = device.get_result()
            # todo 有很多封面的layout为空
            yield (element for element in layout if isinstance(element, LTTextBoxHorizontal))


def bsearch(arr, tb):
    """二分查找可加入的row，若找不到则返回应插入的位置"""
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) >> 1
        if arr[mid].y1 - 4 <= tb.y1 <= arr[mid].y1 + 4:
            return False, mid
        elif arr[mid].y1 - 4 > tb.y1:
            high = mid - 1
        else:
            low = mid + 1
    return True, low


def main(fn):
    """将pdfminer解析得到的textboxes按y1值进行分组"""
    res = []
    laparams = LAParams(line_margin=0.2)
    pages = get_pages(fn, laparams)
    for page_no, textboxes in enumerate(pages, start=1):
        arr = []
        for tb in textboxes:
            insert, idx = bsearch(arr, tb)
            if insert:
                container = LTExpandableContainer()
                container.add(tb)
                arr.insert(idx, container)
            else:
                arr[idx].add(tb)
        arr.sort(key=lambda x: -x.y0)
        for line_no, container in enumerate(arr, start=1):
            container._objs.sort(key=lambda x: x.x0)
            # print(round(container.height, 2), [tb.get_text().replace('\n', '') for tb in container])
            # print(page_no, line_no, [tb.get_text().replace('\n', '') for tb in container])
            line = [tb.get_text().replace('\n', '') for tb in container]
            res.append({'page_no': page_no, 'line_no': line_no, 'data': line})
    return res


def get_cover_info(cover_data):
    assert cover_data[0]['data'][0].startswith('*') and cover_data[0]['data'][0].endswith('*')
    assert cover_data[2]['data'][0] == '连云港市第一人民医院体检中心'
    assert cover_data[5]['data'][0] == '姓    名'
    assert cover_data[6]['data'][0] == '性    别'
    assert cover_data[7]['data'][0] == '年    龄'
    assert cover_data[11]['data'][0] == '体检日期'
    basic_info = {
        '流水号': cover_data[1]['data'][0],
        '体检编号': cover_data[4]['data'][1],
        '姓名': cover_data[5]['data'][1],
        '性别': cover_data[6]['data'][1],
        '年龄': cover_data[7]['data'][1],
        '联系电话': cover_data[8]['data'][1] if len(cover_data[8]['data']) == 2 else None,
        '单位': cover_data[9]['data'][1],
        '部门': cover_data[10]['data'][1],
        # arrow.get(a, 'YYYY年MM月DD日')
        '体检日期(封面)': cover_data[11]['data'][1],
        '体检日期(页眉)': f"20{cover_data[1]['data'][0][:6]}",
    }
    return basic_info


def get_flags(lines):
    flags = {'操作员': []}
    for index_, line in enumerate(lines):
        data = line['data']
        if data[0].startswith('检查综述'):
            flags['检查综述起'] = index_
        if data[0].startswith('医生建议'):
            flags['检查综述终'] = index_
        if data[0].startswith('总检日期'):
            flags['总检日期'] = index_
        if '总检日期' in flags and data[0].startswith('姓名') and (index_ - flags['总检日期'] <= 4):
            flags['第一个检查项'] = index_ + 1
        if data[0].startswith('操作员'):
            flags['操作员'].append(index_)
    return flags


def get_summary(lines, flags):
    summary = ''
    for index_, line in enumerate(lines):
        if flags['检查综述起'] <= index_ < flags['检查综述终']:
            summary += f"\n{line['data'][0]}"
    return summary


def get_group_names(slices, flags, i):
    slices = lines[flags['操作员'][i] + 1:flags['操作员'][i + 1]]
    if slices[0]['data'][0][:4] not in ['连云港市', '咨询电话', '姓名：']:
        group_name = slices[0]['data'][0]
        return group_name
    else:
        raise ValueError('group_name 不合法！') from None

def get_group_samples(slices):
    group_samples = []
    for samples in slices[1:]:
        if samples['data'][0][:4] not in ['连云港市', '咨询电话', '姓名：']:
            group_samples.append(samples['data'])
    return group_samples


def get_samples(lines):
    flags = get_flags(lines)
    res = {}
    summary = get_summary(lines, flags)
    res['综述'] = summary

    for i in range(len(flags['操作员']) - 1):
        slices = lines[flags['操作员'][i] + 1:flags['操作员'][i + 1]]
        group_name = get_group_names(slices, flags, i)
        print(f'{group_name: ^30}')
        group_samples = get_group_samples(slices)
        pprint(group_samples)
        break

    # if index_ > flags['第一个检查项'] and line['data'][0].startswith('操作员'):
    #     group_sep_index = index_


if __name__ == '__main__':
    a = time.time()
    paths = glob.glob('/Users/har/Desktop/连云港第一人民医院526/*.pdf')
    fails = 0
    for path in paths:
        # path = '/Users/har/Desktop/连云港第一人民医院526/o2UrD0gdNAuigatnFnTnhqocmtZE.pdf'
        lines = main(path)
        cover_data = [line for line in lines if line['page_no'] == 1]
        get_samples(lines)
        print(path)
        break
        # if not cover_data:
        #     pass
        # else:
        #     basic_info = get_cover_info(cover_data, path)
