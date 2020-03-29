"""Use pdfminer to extract textbox rows from PDF"""
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


if __name__ == '__main__':
    path = '/Users/har/Desktop/pdf/o2UrD0hMwrwTzqEX_0saTeJ-9M14.pdf'
    lines = main(path)
 