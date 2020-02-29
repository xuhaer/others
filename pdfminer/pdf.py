"""Use pdfminer to extract textbox rows from PDF"""
import os
import re
import json
import time
import glob

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
    laparams = LAParams(line_margin=0.32)
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
        for container in arr:
            container._objs.sort(key=lambda x: x.x0)
            line = [tb.get_text().replace('\n', '') for tb in container]
            # print(round(container.height, 2), line)
            res.append({'page_no': page_no, 'data': line})
    return res



def get_cover_info(cover_data):
    assert cover_data[0]['data'][0].startswith('南京鼓楼')
    assert cover_data[1]['data'][0].startswith('健康')
    assert cover_data[2]['data'][0].startswith('档 案 号')
    assert cover_data[3]['data'][0].startswith('姓    名')
    assert cover_data[4]['data'][0].startswith('单位名称')
    assert cover_data[5]['data'][0].startswith('总检日期')
    assert cover_data[8]['data'][0].startswith('部    门')
    assert cover_data[9]['data'][0].startswith('手    机')
    # assert cover_data[12]['data'][1].startswith('体检号')
    for data in cover_data:
        if '龄' in str(data) and '性' in str(data):
            sex_age = data['data']
        if '体检号' in str(data):
            check_num = data['data']
    basic_info = {
        '档案号': cover_data[2]['data'][1].strip(),
        '姓名': cover_data[3]['data'][1].strip(),
        '单位名称': cover_data[4]['data'][1].strip(),
        '总检日期': cover_data[5]['data'][1].strip(),
        '性别': sex_age[1].split('：')[1].strip(),
        '年龄': sex_age[2].split('：')[1].replace('岁', '').strip(),
        '部门': cover_data[8]['data'][1].strip() if len(cover_data[8]['data']) == 2 else None,
        '手机': cover_data[9]['data'][1].strip() if len(cover_data[9]['data']) == 2 else None,
        '体检号': re.search(r'体检号：(\d)*', ''.join(check_num))[0].split('：')[1].strip(),
    }
    return basic_info


def basic_info_from_content(lines):
    for line in lines:
        data = line['data']
        if data[0] == '姓名：':
            return {
                '姓名': data[1],
                '性别': data[2].replace('性别：', ''),
                '年龄': re.search(r'\d+', data[3])[0],
                '流水号': data[5],
                '体检日期': data[6].replace('体检日期：', ''),
            }


def get_flags(lines):
    flags = {'项目指标锚点': []}
    for index_, line in enumerate(lines):
        data = line['data']
        if data[0].startswith('本次体检中存在的异常提示'):
            flags['检查综述起'] = index_
        if data[0].startswith('总检建议'):
            flags['检查综述终'] = index_
        if '检查医生' in str(data):
            flags['项目指标锚点'].append(index_)
    flags['项目指标锚点'].append(len(lines)) # 强制标记结尾，有冗余
    # if flags.keys() != {'项目指标锚点', '检查综述起', '检查综述终'}:
    #     raise ValueError('信息不全')
    return flags


def get_summary(lines, flags):
    summary = ''
    for index_, line in enumerate(lines):
        if flags['检查综述起'] <= index_ < flags['检查综述终']:
            summary += f"\n{'  :'.join(line['data'])}"
    return summary


def get_group_names(slices):
    for sl in slices:
        # 跨页时有页眉页脚多余数据:
        for other_info in ['南京鼓楼', '地址', '---姓', '姓名']:
            if not other_info in sl['data'][0]:
                group_name = sl['data'][0]
                return group_name


def get_group_samples(slices):
    group_samples = []
    for samples in slices[1:]:
        if not (samples['data'][0].startswith('项目名称') or \
        samples['data'][0].startswith('南京') or \
        samples['data'][0].startswith('检查结果') or \
        samples['data'][0].startswith('地址') or \
        samples['data'][0].startswith('姓名') or \
        samples['data'][0] == ' ' or \
        samples['data'][0].startswith('---姓')):
            group_samples.append(samples['data'])
    return group_samples


def parsing_common_samples(group_samples, group_name):
    res = []
    for line in group_samples:
        if '项目名称' in str(line):
            continue
        if len(line) == 1:
            if '小结' in str(line):
                res.append({'group_name': group_name, 'item_name': f'{group_name.strip()}小结', 'value': line[0].strip()})
            elif not (line[0].startswith('辅诊') or \
                line[0].startswith('实验室') or \
                line[0].startswith('(FPSA)') or \
                line[0].startswith('心电图检查报告') or \
                line[0].startswith('辅诊')):
                res[-1]['value'] += line[0].strip()
            else:
                print(f'请注意line{line} 是否为无效数据??')
                # raise ValueError('未知数据格式！{line}') from None
        elif len(line) == 2:
            res.append({'group_name': group_name, 'item_name': line[0].strip(), 'value': line[1].strip()})
        elif len(line) in [3, 4, 5]:
            if len(line) == 3 and line[2].strip() == '异常':# 彩超提示
                res.append({'group_name': group_name, 'item_name': line[0].strip(), 'value': line[1].strip()})
                continue
            refrange = None
            for data in line:
                if re.search(r'\d+\.?\d*-+\d+\.?\d*', str(data)) or (set('<=>') & set(data)):
                    refrange = data
            if refrange:
                res.append({'group_name': group_name, 'item_name': line[0].strip(), 'value': line[1].strip(), 'refrange': refrange})
            else:
                res.append({'group_name': group_name, 'item_name': line[0].strip(), 'value': line[1].strip()})
        else:
            raise ValueError(f'体检数据未知的长度格式:{line}') from None
    return res


def parsing_samples(group_name, group_samples):
    res = parsing_common_samples(group_samples, group_name)
    # if '项目名称' in str(group_samples):
    #     res = parsing_common_samples(group_samples, group_name)
    # else:
    #     res = parsing_divide_samples(group_samples, group_name)
    return res


def get_data(lines):
    flags = get_flags(lines)
    try:
        summary = get_summary(lines, flags)
    except Exception:
        summary = ''
    all_samples = []
    for i in range(len(flags['项目指标锚点']) - 1):
        slices = lines[flags['项目指标锚点'][i]:flags['项目指标锚点'][i + 1]]
        if not slices:
            continue
        # group_name = get_group_names(slices)
        group_name = lines[flags['项目指标锚点'][i]]['data'][0].strip()
        group_name = group_name.replace('项目名称', '').strip()
        if not group_name:
            print(f'请注意group_name{slices} 是否为无效数据??')
            continue
        group_samples = get_group_samples(slices)
        if not group_samples:
            print(f'请注意group_samples{slices} 是否为无效数据??')
            continue
        samples = parsing_samples(group_name, group_samples)
        all_samples.extend(samples)
    return {'summary': summary, 'samples': all_samples}


if __name__ == '__main__':
    a = time.time()
    res = []
    paths = glob.glob('/Users/har/Desktop/pdf/*.pdf')
    for path in paths:
        # path = '/Users/har/Desktop/pdf/o2UrD0hMwrwTzqEX_0saTeJ-9M14.pdf'
        lines = main(path)
        if not lines:
            # pdf 不含文字内容，全为图片
            res.append({'file_name': path})
            continue
        cover_data = [line for line in lines if line['page_no'] <= 2]
        if not cover_data:
            raise ValueError(f'该份报告没有封面信息！----{path}')
            # basic_info = basic_info_from_content(lines)
        else:
            try:
                basic_info = get_cover_info(cover_data)
            except Exception as e:
                print(path)
        data = {'file_name': os.path.basename(path), 'basic_info': basic_info}
        data.update(get_data(lines))
        res.append(data)
    with open('/Users/har/Desktop/pdf1.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(time.time() - a)
