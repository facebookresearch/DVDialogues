"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json 
import pdb
import copy
import glob 
import pandas as pd

def display_template(file, idx, t):
    '''
    print('==========={} {}========='.format(file, idx))
    print(t['text'][0]) 
    
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print(t['constraints'])
    #if 'interval_type' in t: 
    print('Interval type {}'.format(t['interval_type']))
    if 'unique_obj' in t: print('Unique obj {}'.format(t['unique_obj']))
    if 'answer_obj' in t: print('Answer obj {}'.format(t['answer_obj']))
    if 'all_unique_objs' in t: print('All unique obj {}'.format(t['all_unique_objs']))
    if 'ref_constraints' in t: print('Ref Constraint: {}'.format(t['ref_constraints']))
    if 'ref_remark' in t: print(t['ref_remark'])
    if 'remark' in t: print(t['remark'])
    '''

def load_file(file):
    print("Loading template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(data, file):
    new_file = file.replace('_4.json', '_5.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)
    
def save_file2(data, file):
    new_file = file.replace('_5.json', '_6.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)

node_type_to_attribute = {'query_size': '<Z>', 'query_shape': '<S>', 'query_color': '<C>', 'query_material': '<M>'}
for file in glob.glob('*5.json'):
    data = load_file(file)
    new_data = []
    for d_idx, d in enumerate(data):
        if d['nodes'][-1]['type'] in node_type_to_attribute and d['interval_type']!='none':
            continue
        new_data.append(d)
        if 'zero_hop' in file and 'What types of actions' in d['text'][0]:
            new_template = copy.deepcopy(d)
            new_template['interval_type'] = 'atomic'
            new_data.append(new_template)
            
            new_d = copy.deepcopy(d)
            new_d['text'] = ['What types of actions does the <Z> <C> <M> <S> undertake <O> ?', 
                         'What activities that the <Z> <C> <M> <S> perform <O> ?', 
                         'What is the <Z> <C> <M> <S> doing <O> ?']
            new_d['nodes'][2]['type'] = 'query_action_order'
            new_d['nodes'][2]['side_inputs'] = ['<O>']
            new_d['params'].append({'type': 'Ordinal', 'name': '<O>'})
            new_data.append(new_d)
            
            new_d = copy.deepcopy(d)
            new_d['text'] = ['What types of actions does the <Z> <C> <M> <S> undertake exactly <F> ?', 
                         'What activities that the <Z> <C> <M> <S> perform exactly <F> ?']
            new_d['nodes'][2]['type'] = 'query_action_freq'
            new_d['nodes'][2]['side_inputs'] = ['<F>']
            new_d['params'].append({'type': 'Frequency', 'name': '<F>'})
            new_data.append(new_d) 
     
    save_file2(new_data, file)

count = 0 
for file in glob.glob('*6.json'):
    data = load_file(file)
    for d_idx, d in enumerate(data):
        display_template(file, d_idx, d)
        count += 1 
print("Final number of question templates:{}".format(count))
