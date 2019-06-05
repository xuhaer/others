import json
from collections import defaultdict

import jieba
import pandas as pd


class SampleClassifier:
    '''
    指标名称分类器.
    以 SampleType 表为依据对传入指标进行指标预测，返回可能性最大的几个标准指标
    input: organization(机构名，默认为空)
    '''
    def __init__(self, st_json_path, organization=None, threshold=0.1):
        self.organization = organization
        self.threshold = threshold
        self.st_json_path = st_json_path
        self.st_words_data = None
        self.st_json_data = None

    def std_data(self):
        '''
        生成标准指标名称分词数据:
        {指标 ID: [{'nameChs 分词词汇'}, {'nameChsAlts 分词词汇'}, [全匹配名称词汇]]}
        '''
        with open(self.st_json_path) as f:
            self.st_json_data = json.load(f)
        st_words_dict = defaultdict(list)

        for st in self.st_json_data:
            st_id, nameChs, nameChsAlts = st['sampleTypeId'], st['nameChs'], st['nameChsAlts']
            name, nameAlts = st['name'], st['nameAlts']
            if nameChs:
                st_words_dict[st_id].append(set(jieba.cut(nameChs)))
            else:
                st_words_dict[st_id].append(set())
            if nameChsAlts:
                st_words_dict[st_id].append(set(jieba.cut(nameChsAlts)))
            else:
                st_words_dict[st_id].append(set())
            name_list = nameAlts.split(',')
            name_list.extend([name, nameChs, nameChsAlts])
            # 特殊处理
            if 'PGⅠ/PGⅡ' in name_list:
                name_list.append('PGI/PGII')
            st_words_dict[st_id].append(name_list)
            self.st_words_data = st_words_dict

    def name_similarity(self, sample):
        """指标名称相似度"""
        res = []
        if not 'nameChs' in sample:
            raise ValueError('计算指标相似度至少需要提供第三方指标中文名:`nameChs`')
        sample_words_set = set(jieba.cut(sample['nameChs']))
        if not self.st_words_data:
            self.std_data()
        for st_id, st_words_list in self.st_words_data.items():
            similarity = 0
            nameChs_set, nameChsAlts_set = st_words_list[0], st_words_list[1]
            # 尝试名称全匹配:
            if sample['name'] in st_words_list[2] or sample['nameChs'] in st_words_list[2]:
                similarity += 1
            if nameChs_set:
                joined_set = sample_words_set & nameChs_set
                sim_len = len(joined_set)
                total_len = max(len(sample_words_set), len(nameChs_set))
                # 若交集词汇中有长度>1的词汇，提升其相似性:
                words_len_factor = 1.2 if any([len(x) > 1 for x in joined_set]) else 1
                similarity += round(words_len_factor * (sim_len / total_len), 4)
                # nameChsAlts修正:
                correct_sim_len, correct_factor = len(sample_words_set & nameChsAlts_set), 0.2
                correct_similarity = round(correct_factor * (correct_sim_len / total_len), 4)
                if correct_similarity:
                    similarity += round(correct_similarity, 4)
            else:
                sim_len, factor = len(sample_words_set & nameChsAlts_set), 1
                total_len = max(len(sample_words_set), len(nameChsAlts_set))
                similarity += round(factor * (sim_len / total_len), 4)

            if similarity > self.threshold:
                res.append({
                    '相似度': similarity,
                    '指标': list(filter(lambda x: x['sampleTypeId'] == st_id, self.st_json_data))[0]
                })
        return res

    def unit_recorrect(self, sample, res):
        for sim_info in res:
            st = sim_info['指标']
            if st['unit'] == sample.get('unit', None):
                sim_info['相似度'] += 0.5
        return sorted(res, key=lambda x: x['相似度'], reverse=True)[:5]

    def refrange_recorrect(self, sample, res):
        return res

    def predict(self, sample):
        name_similarity = self.name_similarity(sample)
        res = self.unit_recorrect(sample, name_similarity)
        return res


def run():
    SC = SampleClassifier('st.json')
    df = pd.read_excel('/Users/har/Desktop/内蒙汇总数据_v2_评估.xlsx')

    map_list = []
    sim_list = []

    for line in df.values:
        nameChs, name = line[0], line[1]
        sample = {'name': name, 'nameChs': nameChs, 'unit': line[2]}
        predict = SC.predict(sample)
        if predict:
            map_list.append(predict[0]['指标']['name'])
            sim_list.append('，'.join([x['指标']['name'] for x in predict[1:]]))
        else:
            map_list.append('')
            sim_list.append('')
    df['map_list'] = map_list
    df['sim_list'] = sim_list

    df.to_excel('/Users/har/Desktop/内蒙汇总数据_v5_评估.xlsx')

run()

