"""Use pdfminer to extract textbox rows from PDF"""
import json
import time
import re
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
            line = [tb.get_text().replace('\n', '') for tb in container]
            # print(round(container.height, 2), line)
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
        '体检日期': cover_data[11]['data'][1],
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
    flags = {'操作员': []}
    for index_, line in enumerate(lines):
        data = line['data']
        if data[0].startswith('检查综述'):
            flags['检查综述起'] = index_
        if data[0].startswith('医生建议'):
            flags['检查综述终'] = index_
        if data[0].startswith('操作员') or data[0].startswith('总检日期'):
            flags['操作员'].append(index_)
    return flags


def get_summary(lines, flags):
    summary = ''
    for index_, line in enumerate(lines):
        if flags['检查综述起'] <= index_ < flags['检查综述终']:
            summary += f"\n{line['data'][0]}"
    return summary


def get_group_names(slices):
    for sl in slices:
        if sl['data'][0][:4] not in ['连云港市', '咨询电话', '姓名：']:
            group_name = sl['data'][0]
            return group_name
        else:
            continue
    raise ValueError('group_name 不合法！') from None


def get_group_samples(slices):
    group_samples = []
    for samples in slices[1:]:
        if samples['data'][0][:4] not in ['连云港市', '咨询电话', '姓名：']:
            group_samples.append(samples['data'])
    return group_samples


def parsing_common_samples(group_samples, group_name):
    res = []
    for line in group_samples:
        if len(line) == 1:
            continue
        elif len(line) == 2:
            if line[0].startswith('小结：'):
                res.append({'group_name': group_name, 'item_name': f'{group_name}小结', 'value': line[1]})
            elif line[0] != '项目名称':
                res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            else:
                continue
        elif len(line) in [3, 4, 5]:
            if '项目名称' in str(line) or '单位' in str(line): continue
            if ['项目名称', '检查结果', '单位', '参考值', '提示'] in group_samples:
                refrange = None
                # ['RBC分布宽度(CV)', '12.6', '11-16'] 无单位的情况，当然后面可有提示值
                # ['维生素C', '-', 'nmol/L']           无参考值的情况
                for data in line:
                    if re.search(r'\d+\.?\d*-+\d+\.?\d*', str(data)) or (set('<=>') & set(data)):
                        refrange = data
                if refrange:
                    res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1], 'refrange': refrange})
                else:
                    res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            else:
                raise ValueError(f'体检数据未知的长度格式:{line}') from None
        else:
            raise ValueError(f'体检数据未知的长度格式:{line}') from None
    return res


def parsing_divide_samples(group_samples, group_name):
    res = []
    for line in group_samples:
        if len(line) == 1:
            continue
        elif len(line) == 2:
            if line[0].startswith('小结：'):
                res.append({'group_name': group_name, 'item_name': f'{group_name}小结', 'value': line[1]})
            elif line[0].startswith('其') or line[0].startswith('液基细胞'):# 其它 和 其他
                res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            elif '视力' in line[0]:
                for l in line:
                    if len(l.split()) == 2:
                        res.append({'group_name': group_name, 'item_name': l.split()[0], 'value': l.split()[1]})
                    else:
                        continue
            else:
                continue
        elif len(line) == 3:
            # ['宫颈', '宫颈肥大  宫颈糜烂Ⅱ度', '子宫体位置 正常']
            if line == ['身高', 'Cm', '体重']:
                continue
            if len(line[2].split()) != 2:
                continue
            res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            res.append({'group_name': group_name, 'item_name': line[2].split()[0], 'value': line[2].split()[1]})
        elif len(line) == 4:
            # ['家族史', '无', '既往史', '无']
            res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            res.append({'group_name': group_name, 'item_name': line[2], 'value': line[3]})
        elif len(line) == 5:
            # ['身高', '162.3', 'Cm', '体重', '56.0']
            res.append({'group_name': group_name, 'item_name': line[0], 'value': line[1]})
            res.append({'group_name': group_name, 'item_name': line[3], 'value': line[4]})
        else:
            raise ValueError(f'体检数据未知的长度格式:{line}') from None
    return res


def parsing_samples(group_name, group_samples):
    if '项目名称' in str(group_samples):
        res = parsing_common_samples(group_samples, group_name)
    else:
        res = parsing_divide_samples(group_samples, group_name)
    return res


def get_data(lines):
    flags = get_flags(lines)
    summary = get_summary(lines, flags)
    all_samples = []
    for i in range(len(flags['操作员']) - 1):
        slices = lines[flags['操作员'][i] + 1:flags['操作员'][i + 1]]
        group_name = get_group_names(slices)
        group_samples = get_group_samples(slices)
        samples = parsing_samples(group_name, group_samples)
        all_samples.extend(samples)
    return {'summary': summary, 'samples': all_samples}


if __name__ == '__main__':
    a = time.time()
    res = []
    paths = glob.glob('/Users/har/Desktop/连云港第一人民医院534/*.pdf')
    for path in paths:
        lines = main(path)
        if not lines:
            # pdf 不含文字内容，全为图片
            print(path)
            res.append({'file_name': path})
            continue
        cover_data = [line for line in lines if line['page_no'] == 1]
        if not cover_data:
            basic_info = basic_info_from_content(lines)
        else:
            basic_info = get_cover_info(cover_data)
        data = {'file_name': path, 'basic_info': basic_info}
        data.update(get_data(lines))
        res.append(data)
        print('ok', end=' ')
    with open('/Users/har/Desktop/data2.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(time.time() - a)
