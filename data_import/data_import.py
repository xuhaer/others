import json
import re


from datetime import datetime
from collections import defaultdict

import pymysql.cursors
import pandas as pd

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='123321',
                             db='cms',
                             charset='utf8mb4',
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor)

cursor = connection.cursor()

cursor.execute('''ALTER TABLE app_4_sampletype MODIFY name VARCHAR(40) BINARY;''')
connection.commit() # NAME PCT-001 和Pct-001并存
cursor.execute('''ALTER TABLE app_4_samplerisk MODIFY code VARCHAR(20) BINARY;''')
connection.commit() # code PCT-001 和Pct-001并存


def before_work():
    '''import sampleType data from the csv data exported by Dbeaver'''

    sample_type_data = pd.read_csv("/Users/har/Desktop/T_SampleType.csv")
    sample_type_data = sample_type_data[['sampleTypeId', 'name','nameChs','dataType','unit','description','shortDescription']]

    def data_type_trans(x):
        if x == 'float':
            return 2
        elif x == 'int':
            return 1
        else:
            return 3
        
    sample_type_data['dataType'] = sample_type_data['dataType'].map(data_type_trans)
    sample_type_data.columns = ['id', 'name','nameChs','dataType','units','description','short_description']
    sample_type_data.index = sample_type_data.index +1
    sample_type_data.fillna('',inplace=True)
    # print(sample_type_data.tail())



    sampletype_list = []
    sp_name_to_id = {} # sampleType name --> sampleType Id

    for st in sample_type_data.values:
        sample_type = [st[i] for i in range(7)]
        sampletype_list.append(sample_type)
        sp_name_to_id[st[1]] = st[0]

    return sampletype_list, sp_name_to_id


def gen_tag_name_to_id():
    '''tag name --> tagId'''
    cursor.execute('''select id,name from app_4_tag;''')
    connection.commit()
    rows = cursor.fetchall()
    tag_name_to_id = {}
    for row in rows:
        tag_name_to_id[row['name']] = row['id']
    if not tag_name_to_id:
        print('请先导入Tag表的数据')
    return tag_name_to_id


def gen_all_tag_data():
    '''GROUP_TYPE = ((0, ''), (1, u'疾病'), (2, u'风险'), (3, u'描述'), (4, u'统计'))
    '''
    g_map = {0:'', 1:'疾病', 2:'风险', 3:'描述', 4:'统计'}
    all_tag_data = {} # k:关键词,value:标签类型，系统，子分类, code
    data = pd.read_excel('/Users/har/Desktop/标签latest.xlsx',sheet_name='描述标签')
    data[['系统', '分类']] = data[['系统', '分类']].fillna('其它')
    for d in data.values:
        if d[2] in all_tag_data.keys():
            raise Exception('标签名:{}不唯一，同时存在于{}和{}中!'.format(d[2], g_map[all_tag_data[d[2]]['类型']], '描述标签'))
        all_tag_data[d[2]] = {'类型':3, '系统':d[0], '子分类':d[1],'code':'无'}
    # print(all_tag_data)


    data1 = pd.read_excel('/Users/har/Desktop/标签latest.xlsx',sheet_name='风险标签')
    data1 = data1[['系统', '分类', '关键词','风险代码']]

    def tag_trans(x):
        '''tag-R3,R4 -->tag-R3,tag-R4'''
        if isinstance(x,str) :
            tag_list = x.split(',')
            for x in range(len(tag_list)):
                if len(tag_list[x]) ==2:
                        tag_list[x] =  tag_list[x-1][:-2] + tag_list[x]
            return(','.join(tag_list))
        else:return x

    data1['风险代码'] = data1['风险代码'].map(tag_trans)
    data1['风险代码'] = data1['风险代码'].fillna('无')
    data1[['系统', '分类']] = data1[['系统', '分类']].fillna('其它')

    for d in data1.values:
        if d[2]:# 排除空行
            if d[2] in all_tag_data.keys():
                raise Exception('标签名:{}不唯一，同时存在于GROUP_TYPE={}和{}中!'.format(d[2], g_map[all_tag_data[d[2]]['类型']], '风险标签'))
            all_tag_data[d[2]] = {'类型':2, '系统':d[0], '子分类':d[1],'code':d[3]}
    # print(all_tag_data)

    data2 = pd.read_excel('/Users/har/Desktop/标签latest.xlsx',sheet_name='疾病标签')
    data2 = data2[['系统', '分类', '关键词', '风险代码']]
    # data2.head()
    data2['风险代码'] = data2['风险代码'].map(tag_trans)
    data2['风险代码'] = data2['风险代码'].fillna('无')
    data2[['系统', '分类']] = data2[['系统', '分类']].fillna('其它')

    # data2.head()
    for d in data2.values:
        if d[2]:
            if d[2] in all_tag_data.keys():
                raise Exception('标签名:{}不唯一，同时存在于GROUP_TYPE={}和{}中!'.format(d[2], g_map[all_tag_data[d[2]]['类型']], '疾病标签'))
            all_tag_data[d[2]] = {'类型':1, '系统':d[0], '子分类':d[1], 'code':d[3]}
    

    # data3 = pd.read_excel('/Users/har/Desktop/个人-统计标签映射表textjoin后.xlsx',sheet_name='Sheet1')
    # data3 = data3.iloc[:, :3]
    # # data3.head()
    # for d in data3.values:
    #     if d[2]:
    #         for tag in d[2].split(','):
    #             if not tag in all_tag_data.keys():
    #                 # print(d)
    #                 raise Exception('团体标签:{} 在标签表中不存在!'.format(d))

    with open('/Users/har/Desktop/all_tag_data.json', 'w') as f:
        json.dump(all_tag_data, f, ensure_ascii=False, indent=4)


gen_all_tag_data()


with open('/Users/har/Desktop/all_tag_data.json', 'r') as f:
    all_tag_data = json.load(f)


def import_taggroup():
    taggroup_data = []
    temp_data = []
    for v in all_tag_data.values():
        # taggroup_data: name:'系统'-'子分类'
        temp_data = [v['系统'] + '-' + v['子分类'],v['类型']]
        if not temp_data in taggroup_data:
            taggroup_data.append(temp_data)
    # print(len(taggroup_data))#[['内分泌代谢-性激素', 1]]
    # 补充团体标签组
    data3 = pd.read_excel('/Users/har/Desktop/个人-统计标签映射表textjoin后.xlsx',sheet_name='Sheet1')
    data3 = data3.iloc[:, :3]
    for d in data3.values:
        if d[2] and not [d[0] + '-' + d[1], 4] in taggroup_data:
            taggroup_data.append([d[0] + '-' + d[1], 4])
    # print(taggroup_data[-2])#[['内分泌代谢-性激素', 1]]
    
    try:
        cursor.executemany('''insert into app_4_taggroup(name, group_type, create_time, write_time)
            values(%s, %s, "2018-08-21 19:56:45", "2018-08-21 19:56:45" )''',taggroup_data)
        connection.commit()

    except Exception as e:
        print('import_taggroup error:',e)
        connection.rollback()


def import_tag():
    tag_data = []
    for v in all_tag_data.keys():
        tag_data.append([v, ])

    # for i in range(3999):
    #     try:
    #         name = "test" + str(i)
    #         cursor.execute('''insert into app_4_sampletype(name, nameChs,dataType, units, description, short_description, create_time, write_time)
    #             values(name, "测试", 2, "g/L", "描述", "描述", "2018-08-21 17:56:45", "2018-08-21 17:56:45")''')
    #         connection.commit()
    #     except Exception as e:
    #         print('sample_type_import error:',e)
    #         connection.rollback()

    try:
        cursor.executemany('''insert into app_4_tag(name, create_time, write_time)
            values(%s, "2018-08-21 19:56:45", "2018-08-21 19:56:45")''',tag_data)
        connection.commit()

    except Exception as e:
        print('import_tag error:',e)
        connection.rollback()


def import_taggroupmembers():
    '''foreign key:tag,taggroup'''
    # taggroupmembers_map = {}
    taggroupmembers_map = defaultdict(list)

    for k,v in all_tag_data.items():
        '''tag_name -->tag_group_name'''
        taggroupmembers_map[k].append(v['系统'] + '-' + v['子分类'])
    # print(len(taggroupmembers_map))

    # 补充团体标签数据
    data3 = pd.read_excel('/Users/har/Desktop/个人-统计标签映射表textjoin后.xlsx',sheet_name='Sheet1')
    data3 = data3.iloc[:, :3]
    for v in data3.values:
        if v[2]:
            for tag in v[2].split(','):
                # 循环-高血压病 not in [['循环-血管']]
                if not v[0] + '-' + v[1] in taggroupmembers_map[tag]:
                    taggroupmembers_map[tag].append(v[0] + '-' + v[1])

    taggroup = defaultdict(list)
    cursor.execute('''select id,name from app_4_taggroup''')
    connection.commit()
    rows = cursor.fetchall()
    for r in rows:
        taggroup[r['name']].append(r['id'])
    # print(taggroup)

    taggroupmembers_data = []
    cursor.execute('''select id,name from app_4_tag''')
    connection.commit()
    rows = cursor.fetchall()
    for r in rows:
        for tag_group_name in taggroupmembers_map[r['name']]:
            for tag_group_id in taggroup[tag_group_name]:
                taggroupmembers_data.append([r['id'],tag_group_id])
    # print(taggroupmembers_data)

    try:
        cursor.executemany('''insert into app_4_taggroupmembers(tag_id, tag_group_id, create_time, write_time)
            values(%s, %s, "2018-08-21 19:56:45", "2018-08-21 19:56:45")''',taggroupmembers_data)
        connection.commit()

    except Exception as e:
        print(e)
        connection.rollback()


def import_sampletype(sampletype_list):
    '''name unique'''    
    try:
        cursor.executemany('''insert into app_4_sampletype(id, name, nameChs,dataType, units, description, short_description, create_time, write_time)
            values(%s, %s, %s, %s, %s, %s, %s, "2018-08-21 19:56:45", "2018-08-21 19:56:45")''',sampletype_list)
        connection.commit()

    except Exception as e:
        print('sample_type_import error:',e)
        connection.rollback()


def import_sampletypegroup():
    '''name unique'''
    pass


def import_sampletypegroupmembers():
    '''foreign key:sampletype,sampletypegroup'''
    pass


def import_samplerisk(sp_name_to_id):
    '''foreign key:sampletype,tag'''

    with open('/Users/har/Desktop/deds.json') as f:
        ded_data = json.load(f)
    pattern = re.compile("'code': '(.*?)'")
    all_risk_codes = pattern.findall(str(ded_data))
    risk_code_to_tag_name = defaultdict(list)

    for k,v in all_tag_data.items():
        if v['code'] != '无':
            for code in v['code'].split(','):
                if not code in all_risk_codes:
                    raise Exception('{} 不在deds.json中！'.format(code))
                risk_code_to_tag_name[code].append(k)
    # print(risk_code_to_tag_name)

    tag_name_to_id = gen_tag_name_to_id()
    # print(2222222,tag_name_to_id)

    try:
        cursor.execute('''select id,name from app_4_sampletype''')
        connection.commit()
        rows = cursor.fetchall()

        sp_name_to_id = {}
        sample_risk = []
        for row in rows:
            sp_name_to_id[row['name']] = row['id']
        # print(sp_name_to_id)
        for key in ded_data.keys():
            if not key in sp_name_to_id.keys():
                raise Exception('{} not in sampletype'.format(key))
            for risks in ded_data[key]['tables']:
                ideal = risks['ideal']
                rates = risks['rates']
                for r in rates:
                    # 部分code无对应标签,一个code也可对应多个标签
                    tag_names = risk_code_to_tag_name.get(r['code'])
                    if tag_names:
                        tag_ids = []
                        for tag_name in tag_names:                
                            tag_ids.append(tag_name_to_id[tag_name])
                    else:
                        tag_ids = [None]

                    for tag_id in tag_ids:
                        data = [r['code'],r['color'], r['tip'], str(ideal), r['level'], int(sp_name_to_id[key]), tag_id]
                        sample_risk.append(data)
            
        # print(sample_risk)

    except Exception as e:
        print('select id,name from app_4_sampletype error:',e)
        
    try:
        cursor.executemany('''insert into app_4_samplerisk(code, color, tip, ideal, level, sample_type_id, tag_id, create_time, write_time)
            values(%s, %s, %s, %s, %s, %s, %s, "2018-08-21 19:56:45", "2018-08-21 19:56:45")''',sample_risk)
        connection.commit()
        connection.close()

    except Exception as e:
        print('sample_risk_import error:',e)
        connection.rollback()
        connection.close()


# import_taggroup()
# import_tag()
# import_taggroupmembers()

# sampletype_list, sp_name_to_id = before_work()
# import_sampletype(sampletype_list)
# import_samplerisk(sp_name_to_id)
