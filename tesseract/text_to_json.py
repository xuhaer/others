import re
import json

path = './datasets/数据备份/种信息.txt'
pattern = r'\n([0-9]{1,3}\.\w*)'

with open(path) as f:
    text = f.read()

a = re.split(pattern, text)

snake_chi = a[1::2]
snake_detail = a[2::2]

assert all(['英名' in x for x in snake_detail])
assert all(['依据标本' in x for x in snake_detail])
assert all(['大小' in x for x in snake_detail])
assert all(['特征' in x for x in snake_detail])
assert all(['色斑' in x for x in snake_detail])
assert all(['鳞被' in x for x in snake_detail])
assert all(['栖息环境' in x for x in snake_detail])
assert all(['食物' in x for x in snake_detail])
assert all(['繁殖' in x for x in snake_detail])
assert all(['地理分布' in x for x in snake_detail])

res = []

for index, sd in enumerate(snake_detail):
    snake = {}
    sd_items = sd.split('\n\n')
    assert 11 <= len(sd_items) <= 18

    for item in sd_items[1:]:
        item = item.strip()
        snake['物种名'] = snake_chi[index] + sd_items[0]
        if not len(item) > 1:
            continue
        if item.startswith('英名 '):
            snake['英名'] = item[3:]
        elif item.startswith('依据标本 '):
            snake['依据标本'] = item[5:].strip()
        elif item.startswith('大小 '):
            snake['大小'] = item[3:].strip()
        elif item.startswith('特征 '):
            snake['特征'] = item[3:].strip()
        elif item.startswith('色斑 '):
            snake['色斑'] = item[3:].strip()
        elif item.startswith('鳞被 '):
            snake['鳞被'] = item[3:].strip()
        elif item.startswith('栖息环境 '):
            snake['栖息环境'] = item[5:].strip()
        elif item.startswith('食物 '):
            snake['食物'] = item[3:].strip()
        elif item.startswith('繁殖 '):
            snake['繁殖'] = item[3:].strip()
        elif item.startswith('地理分布 '):
            snake['地理分布'] = item[5:].strip()
        elif item.startswith('垂直分布 '):
            snake['垂直分布'] = item[5:].strip()
        elif item.startswith('我国古籍名 '):
            snake['我国古籍名'] = item[6:].strip()
        elif item.startswith('上颌齿 '):
            snake['上颌齿'] = item[4:].strip()
        elif item.startswith('地方名 '):
            snake['地方名'] = item[4:].strip()
        elif item.startswith('曾用名 '):
            snake['曾用名'] = item[4:].strip()
        elif item.startswith('别名 '):
            snake['别名'] = item[3:].strip()
        elif item.startswith('分类讨论 '):
            snake['分类讨论'] = item[5:].strip()
        elif item.startswith('分类意见 '):
            snake['分类意见'] = item[5:].strip()
        elif item.startswith('附记 '):
            snake['附记'] = item[3:].strip()
        elif item.startswith('图'):
            snake['附图'] = item.strip()
        else:
            print(sd[:20])
            print(item[:20])
    res.append(snake)

with open('./datasets/种信息222.json', 'w') as f:
    json.dump(res, f, ensure_ascii=False, indent=4)
