'''自定义转行规则函数'''

import re


def to_str(key, value):
    return {key: str(value)}


def to_float(key, value):
    '''例子：['177', '弃检'] --> [177, None] '''
    try:
        std_value = float(value)
    except ValueError:
        std_value = None
    return {key: std_value}


def find_numeric(key, value):
    '''
        例子：['4.6偏低', '5偏低', '弃检', '<0.5', '<5', '<=5mmol/l', '<5*10^9/L', '5.6mmol/l']
        -->  [4.6, 5, None, 0.5, 5, 5, 5, 5.6]
    '''
    match = re.search(r'\d+\.?\d*', value)
    if match:
        return to_float(key, match[0])
    else:
        return {key: None}


def to_split(key, value, sep='/'):
    if key == 'BP':
        if len(value.split(sep)) == 2:
            systolic, diastolic = value.split()
            try:
                return {'systolic': int(systolic), 'diastolic':int(diastolic)}
            except ValueError:
                return {'systolic': None, 'diastolic': None}
        else:
            print(value)
            return {'systolic': None, 'diastolic': None}
    else:
        raise ValueError(f'未配置{key}切割规则!') from None
