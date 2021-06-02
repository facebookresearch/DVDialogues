"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json 
import pdb
import copy

"""
    Introduce action for query e.g. what action ... 
    This type of question is for atomic interval only 
    Additional constraint: 
        NOT_NULL_ACT: one of the constraint params need to be a non-empty action 
        STATIC_ACT: the output object of the node (e.g. filter_unique) in constraint params must be stationary/rotating. 
            This is for object used as a base for spatial dependency
        CONTAIN_ACT: param include an action <A> and relation <R>. if relation is 'containing', action only be sliding; if relation is 'contained', action must be empty 
    Additional field in template: 
        interval_type: atomic (each object can have max. 1 action in an atomic interval) 
"""

def display_template(idx, t):
    return 
    print('==========={}========='.format(idx))
    print(t['text'][0]) 
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print(t['constraints'])
    print(t['params'])
    print(t['interval_type'])
    print()
    #pdb.set_trace()
    
def load_file(file):
    file = file.replace('.json', '_1.json')
    print("Adding action query in atomic interval into template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(old_data, data, file):
    data = old_data + data 
    new_file = file.replace('.json', '_2.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)
    
files = ['compare_integer.json']
for file in files:
    data = load_file(file)
    new_data = [] 
    save_file(data, new_data, file)
    
# add similar templates for action e.g. same action 
files = ['comparison.json']
for file in files:
    data = load_file(file)
    new_data = []
    
    for d_idx in [8]:
        d = data[d_idx]
        display_template(d_idx, d)
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][3]['type'] = 'query_action'
        new_d['nodes'][6]['type'] = 'query_action'
        new_d['nodes'][7]['type'] = 'equal_action'
        new_d['constraints'] = [{'params': [2, 5], 'type': 'OUT_NEQ'}, 
                                {'params': ['<A2>'], 'type': 'NULL'}, 
                                {'params': ['<A3>'], 'type': 'NULL'}, 
                                {'type': 'STATIC_ACT', 'params': [1]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A2>', '<R>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)
    
    for d_idx in [12]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][2]['type'] = 'query_action'
        new_d['nodes'][6]['type'] = 'query_action'
        new_d['nodes'][7]['type'] = 'equal_action'
        new_d['constraints'] = [{'params': [1, 5], 'type': 'OUT_NEQ'}, 
                                {'params': ['<A>'], 'type': 'NULL'}, 
                                {'params': ['<A3>'], 'type': 'NULL'}, 
                                {'type': 'STATIC_ACT', 'params': [4]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A3>', '<R>']}] 
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)
    
    for d_idx in [16]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][3]['type'] = 'query_action'
        new_d['nodes'][7]['type'] = 'query_action'
        new_d['nodes'][8]['type'] = 'equal_action'
        new_d['constraints'] = [{'params': [2, 6], 'type': 'OUT_NEQ'}, 
                                {'params': ['<A2>'], 'type': 'NULL'}, 
                                {'params': ['<A4>'], 'type': 'NULL'}, 
                                {'type': 'STATIC_ACT', 'params': [1, 5]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A2>', '<R>']}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A4>', '<R2>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)    
    save_file(data, new_data, file)
    
files = ['same_relate.json', 'zero_hop.json']
for file in files:
    data = load_file(file)
    new_data = []
    save_file(data, new_data, file)
    for d_idx in range(len(data)):
        display_template(d_idx, data[d_idx])
    
files = ['one_hop.json']
for file in files:
    data = load_file(file)
    new_data = [] 
    for d_idx in [2]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['text'] = [
            'What is the <A2> <Z2> <C2> <M2> <S2> [that is] <R> the <Z> <C> <M> <S> doing?', 
            'What types of actions does the <A2> <Z2> <C2> <M2> <S2> [that is] <R> the <Z> <C> <M> <S> undertake?', 
            'What activities does the <A2> <Z2> <C2> <M2> <S2> [that is] <R> the <Z> <C> <M> <S> perform?',
             'There is a <A2> <Z2> <C2> <M2> <S2> [that is] <R> the <Z> <C> <M> <S>. What is it doing?']

        #pdb.set_trace()
        new_d['nodes'][3]['type'] = 'query_action'
        new_d['constraints'] = [{'params': ['<A2>'], 'type': 'NULL'}, 
                                #{'params': [['<Z2>', '<S2>', '<R>', '<Z>', '<S>']], 'type': 'CONTAIN_SHAPE_SIZE'}, 
                                {'type': 'STATIC_ACT', 'params': [1]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A2>', '<R>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)
    save_file(data, new_data, file)
    
files = ['two_hop.json']
for file in files:
    data = load_file(file)
    new_data = []
    for d_idx in [2]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][4]['type'] = 'query_action'
        new_d['constraints'] = [{'params': ['<A3>'], 'type': 'NULL'},  
                                #{'params': [['<Z2>', '<S2>', '<R>', '<Z>', '<S>'], ['<Z3>', '<S3>', '<R2>', '<Z2>', '<S2>']], 'type': 'CONTAIN_SHAPE_SIZE'}, 
                                {'type': 'STATIC_ACT', 'params': [1, 2]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A3>', '<R2>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)
    save_file(data, new_data, file)  
    
files = ['three_hop.json']
for file in files:
    data = load_file(file)
    new_data = []
    for d_idx in [2]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][5]['type'] = 'query_action'
        new_d['constraints'] = [{'params': ['<A4>'], 'type': 'NULL'}, 
                                #{'params': [['<Z2>', '<S2>', '<R>', '<Z>', '<S>'], 
                                #            ['<Z3>', '<S3>', '<R2>', '<Z2>', '<S2>'], 
                                #            ['<Z4>', '<S4>', '<R3>', '<Z3>', '<S3>']], 'type': 'CONTAIN_SHAPE_SIZE'}, 
                                {'type': 'STATIC_ACT', 'params': [1, 2, 3]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A4>', '<R3>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)
    save_file(data, new_data, file)    
    
files = ['single_and.json']
for file in files:
    data = load_file(file)
    new_data = []
    for d_idx in [1]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('size', 'action') for i in new_d['text']]
        new_d['nodes'][8]['type'] = 'query_action'
        new_d['constraints'] = [{'params': [1, 4], 'type': 'OUT_NEQ'}, 
                                {'params': ['<A3>'], 'type': 'NULL'}, 
                                #{'params': [['R3', 'S3', '<R>', '<Z>', '<S>'], 
                                #            ['R3', 'S3', '<R2>', '<Z2>', '<S2>']], 'type': 'CONTAIN_SHAPE_SIZE'}, 
                                {'type': 'STATIC_ACT', 'params': [1, 4]}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A3>', '<R2>']}, 
                                {'type': 'CONTAIN_ACT', 'params': ['<A3>', '<R>']}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)        
    save_file(data, new_data, file)  
    
files = ['single_or.json']
for file in files:
    data = load_file(file)
    new_data = []
    for d_idx in [3]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = [i.replace('<Z3>', '<A3>') for i in new_d['text']]
        new_d['nodes'][5] = {'side_inputs': ['<A3>'], 'inputs': [4], 'type': 'filter_action'}
        new_d['params'].append({'type': 'Action', 'name': '<A3>'})
        new_d['constraints'] = [{'params': [1, 3], 'type': 'OUT_NEQ'}, 
                                {'params': ['<A>'], 'type': 'NULL'}, 
                                {'params': ['<A2>'], 'type': 'NULL'}]
        d['interval_type'] = 'atomic'
        display_template(d_idx, new_d)
        new_data.append(new_d)        
    save_file(data, new_data, file)
