import json


def simplify_json(file_name):
    res = []
    path = '/Users/har/Documents/github/others/'
    with open(f'{path}{file_name}.json') as f:
        origin_data = json.load(f)

    for st in origin_data:
        if st.get('invalid_values'):
            res.append({
                'group_name': st['group_name'],
                'item_name': st['item_name'],
                'invalid_values': st['invalid_values'],
                'value_type': st['value_type'],
                'function': st['function'],
                'std_name': {'name': st['std_name']['name']},
                })
        else:
            res.append({
                'group_name': st['group_name'],
                'item_name': st['item_name'],
                'value_type': st['value_type'],
                'function': st['function'],
                'std_name': {'name': st['std_name']['name']},
            })

    with open(f'{path}{file_name}_精简版.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


simplify_json('滨海县人民医院')


def lazy_json():
    with open('/Users/har/Documents/github/others/配置规则/爱康国宾盐城.json') as f:
        origin_data = json.load(f)

    with open('/Users/har/Documents/github/others/配置规则/爱康国宾连云港.json') as f:
        ref_data = json.load(f)

    for origin_st in origin_data:
        for ref_st in ref_data:
            if origin_st['group_name'] == ref_st['group_name'] and \
                origin_st['item_name'] == ref_st['item_name']:
                # if origin_st['std_name'] != ref_st['std_name']:
                #     print(origin_st['item_name'])
                origin_st['std_name'] = ref_st['std_name']
                origin_st['function'] = ref_st['function']
                # print(origin_st['item_name'])
                break
        print(origin_st['item_name'])

    with open('/Users/har/Documents/github/others/爱康国宾盐城_lazy.json', 'w') as f:
        json.dump(origin_data, f, ensure_ascii=False, indent=2)

# lazy_json()
