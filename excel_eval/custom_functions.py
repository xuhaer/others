'''自定义转行规则函数'''

import re


def to_str(value):
    return str(value)


def to_float(value):
    '''例子：['177', '弃检'] --> [177, None] '''
    try:
        std_value = float(value)
    except ValueError:
        std_value = None
    return std_value


def find_numeric(value):
    '''
        例子：['4.6偏低', '5偏低', '弃检', '<0.5', '<5', '<=5mmol/l', '<5*10^9/L', '5.6mmol/l']
        -->  [4.6, 5, None, 0.5, 5, 5, 5, 5.6]
    '''
    match = re.search(r'\d+\.?\d*', value)
    if match:
        std_value = to_float(match[0])
    else:
        std_value = None
    return std_value
