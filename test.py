import json

with open('res确认后.json') as f:
    SAMPLES_INFO = json.load(f)

with open('./excel_eval/st.json') as f:
    SAMPLETYPE = json.load(f)


for s in SAMPLES_INFO:
    function = s['function']
    std_name = s['std_name']['name']
    value_type = s['value_type']
    value_type_ = max(zip(value_type.values(), value_type.keys()))[1]
    if std_name:
        # 类型保证一致
        st = [s for s in SAMPLETYPE if s['name'] == std_name][0]
        if st['dataType'] in ["[float]", "float", 'int']:
            st_data_type = 'numeric'
        else:
            st_data_type = 'str'
        if value_type_ != st_data_type:
            print(s['item_name'])
    # 保证转换后的值的类型和标准类型一致
    if function == 'str(value)':
        if value_type_ != 'str':
            print(s['item_name'])
    else:
        if value_type_ != 'numeric':
            print(s['item_name'])
