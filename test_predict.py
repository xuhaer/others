import json

from excel_eval.st_db import get_SampleType


SAMPLETYPE = get_SampleType()

with open('爱康国宾配置规则.json') as f:
    data = json.load(f)


def test__not_map():
    print('以下指标无对应规则: ')
    for st in data:
        if not st['std_name']['name']:
            print(st['item_name'])

test__not_map()


def test__invaid_values():
    print('\n \n需注意以下指标对应规则的function: ')
    for st in data:
        invalid_values = st.get('invalid_values')
        if invalid_values:
            for symbol in ['<', '<=', '=', '==', '>', '>=', '!=', '↑', '↓']:
                if symbol in str(invalid_values) and st['function'] != 'find_numeric':
                    print(st['item_name'], '--->', st['function'])
                    break

test__invaid_values()


def test__predict_functions():
    print('\n \n需注意以下指标对应规则的function与对应规则的dataType不匹配: ')
    for st in data:
        ST = [s for s in SAMPLETYPE if s['name'] == st['std_name']['name']]
        if ST and st['function'] == 'to_str':
            if ST[0]['dataType'] != 'text':
                print(st['item_name'], '--->', st['function'])
        elif ST and st['function'] in ['to_float', 'find_numeric']:
            if ST[0]['dataType'] not in ['float', 'int']:
                print(st['item_name'], '--->', st['function'])

test__predict_functions()
