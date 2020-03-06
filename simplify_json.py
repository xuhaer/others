import os
import json
import glob


def simplify_json(origin_path, dest_path):
    '''简化生成好的配置规则'''
    res = []
    with open(origin_path) as f:
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

    with open(dest_path, 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


def auto_correct_json_rule(origin_path, dest_path):
    ''' 为了省时省力，和已经配置好的配置规则做group_name和item_name的全匹配，
        若直接匹配，则将配置好的规则赋值给生成的新规则
    '''
    with open(origin_path) as f:
        origin_data = json.load(f)

    for path in glob.glob('/Users/har/Documents/github/others/参考配置规则/*.json'):
        with open(path) as f:
            ref_data = json.load(f)

        for origin_st in origin_data:
            for ref_st in ref_data:
                if origin_st['group_name'] == ref_st['group_name'] and \
                    origin_st['item_name'] == ref_st['item_name']:
                    # if origin_st['std_name'] != ref_st['std_name']:
                    #     print(origin_st['item_name'])
                    origin_st['std_name']['name'] = ref_st['std_name']['name']
                    origin_st['function'] = ref_st['function']
                    if origin_st['function'] == 'find_numeric' and not origin_st.get('invalid_values'):\
                        origin_st['function'] = 'to_float'

    with open(dest_path, 'w') as f:
        json.dump(origin_data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    for path in glob.glob('/Users/har/Desktop/预测配置结果/*.json'):
        dest_path = '_lazy'.join(os.path.splitext(path))
        auto_correct_json_rule(path, dest_path)
        # dest_path = '_精简版'.join(os.path.splitext(path))
        # simplify_json(path, dest_path)
