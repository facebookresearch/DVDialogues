"
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json 
import pdb
import copy
import pdb 
import shutil

"""
    Copy original templates from CLEVR to the current folder 
    Introduce action as an attribute into questions e.g. the big cube --> the sliding cube
    Additional constraint: 
        NOT_NULL_ACT: one of the constraint params need to be a non-empty action 
        STATIC_ACT: the output object of the node (e.g. filter_unique) in constraint params must be stationary/rotating. 
            This is for object used as a base for spatial dependency
        CONTAIN_ACT: param include an action <A> and relation <R>. if relation is 'containing', action only be sliding; if relation is 'contained', action must be empty 
    Additional field in template: 
        interval_type: atomic (each object can have max. 1 action in an atomic interval) 
            none (no temporal dependency) 
"""

FILES = [
    'compare_integer.json', 'comparison.json', 'same_relate.json', 
    'zero_hop.json', 'one_hop.json', 'two_hop.json', 'three_hop.json',
    'single_and.json', 'single_or.json'
]
template_dir = '/data/users/hle2020/fbsource/archives/clevr-dataset-gen/question_generation/CLEVR_1.0_templates/'
 
for file in FILES:
    shutil.copy(template_dir + file, file)

def display_template(idx, t):
    return 
    print('==========={}========='.format(idx))
    print(t['text'][0]) 
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print(t['constraints'])
    print(t['params'])
    if 'interval_type' in t: print(t['interval_type'])
    print()
    #pdb.set_trace()
    
def load_file(file):
    print("Adding action as an attribute into template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(data, file):
    new_file = file.replace('.json', '_1.json')
    print("Writing updated template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)

files = ['compare_integer.json']
for file in files:
    data = load_file(file)
    old_data = copy.deepcopy(data)
    new_data = []
    
    for d_idx in range(0,3):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none' 
        display_template(d_idx, old_d)
        new_data.append(old_d)
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i2 = tokens.index('<Z2>')
            tokens.insert(i2, '<A2>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_filter_count'
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']='action_filter_count'
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A2>','<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 

    for d_idx in range(3,6):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i3 = tokens.index('<Z3>')
            tokens.insert(i3, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']='relate_action_filter_count'
        d['nodes'][4]['side_inputs'].insert(0, '<A3>')
        d['nodes'][4]['type']='action_filter_count'
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    for d_idx in range(6,len(data)):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i4 = tokens.index('<Z4>')
            tokens.insert(i4, '<A4>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']='relate_action_filter_count'
        d['nodes'][5]['side_inputs'].insert(1, '<A4>')
        d['nodes'][5]['type']='relate_action_filter_count'
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A4>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,4]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A4>','<R2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    save_file(new_data, file)
    
files = ['comparison.json']
for file in files:
    data = load_file(file)
    old_data = copy.deepcopy(data)
    new_data = [] 
    
    for d_idx in range(0,2):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i2 = tokens.index('<Z2>')
            tokens.insert(i2, '<A2>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_filter_unique'
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']='action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A2>','<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    for d_idx in range(2,4):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i2 = tokens.index('<Z2>')
            tokens.insert(i2, '<A2>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_filter_unique'
        d['nodes'][4]['side_inputs'].insert(0, '<A2>')
        d['nodes'][4]['type']='action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A2>','<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d)
    
    for d_idx in [4,7,10,13]:
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i2 = tokens.index('<Z2>')
            tokens.insert(i2, '<A2>')
            i3 = tokens.index('<Z3>')
            tokens.insert(i3, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']='relate_action_filter_unique'
        d['nodes'][5]['side_inputs'].insert(0, '<A3>')
        d['nodes'][5]['type']='action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
        
    for d_idx in [5,8,11,14]:
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i3 = tokens.index('<Z3>')
            tokens.insert(i3, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_filter_unique'
        d['nodes'][5]['side_inputs'].insert(1, '<A3>')
        d['nodes'][5]['type']='relate_action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [4]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A3>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d)
       
    for d_idx in [6,9,12,15]:
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i3 = tokens.index('<Z4>')
            tokens.insert(i3, '<A4>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']='relate_action_filter_unique'
        d['nodes'][6]['side_inputs'].insert(1, '<A4>')
        d['nodes'][6]['type']='relate_action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A4>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,5]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A4>','<R2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d)
        
    save_file(new_data, file)
    
files = ['same_relate.json']
for file in files:
    data = load_file(file)
    old_data = copy.deepcopy(data)
    new_data = []

    for d_idx in range(0,8):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_filter_unique'
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 

    for d_idx in range(8,28):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_' + d['nodes'][1]['type']
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']='action_' +  d['nodes'][3]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A2>','<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    save_file(new_data, file)
    
files = ['zero_hop.json']
for file in files:
    data = load_file(file)
    old_data = copy.deepcopy(data) 
    new_data = []
    for d_idx in range(0,6):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_' + d['nodes'][1]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d)
    save_file(new_data, file)
    
files = ['one_hop.json']
for file in files:
    data = load_file(file)
    for d_idx in range(0,6):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']= d['nodes'][2]['type'].replace('relate_', 'relate_action_')
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)        
    save_file(data, file)
    
files = ['two_hop.json']
for file in files:
    data = load_file(file)
    for d_idx in range(0,6):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z3>')
            tokens.insert(i1, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][3]['side_inputs'].insert(1, '<A3>')
        d['nodes'][3]['type']= d['nodes'][3]['type'].replace('relate_', 'relate_action_')
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,2]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A3>','<R2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)        
    save_file(data, file)   
    
files = ['three_hop.json']
for file in files:
    data = load_file(file)
    for d_idx in range(0,6):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z4>')
            tokens.insert(i1, '<A4>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][4]['side_inputs'].insert(1, '<A4>')
        d['nodes'][4]['type']= d['nodes'][4]['type'].replace('relate_', 'relate_action_')
        d['params'].append({'type': 'Action', 'name': '<A4>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,2,3]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A4>','<R3>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
    save_file(data, file)
    
files = ['single_and.json']
for file in files:
    data = load_file(file)
    for d_idx in range(0,5):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z3>')
            tokens.insert(i1, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][7]['side_inputs'].insert(0, '<A3>')
        d['nodes'][7]['type']= 'action_' + d['nodes'][7]['type']
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        """Fix error of OUT_NEQ"""
        if d_idx==0: 
            d['constraints'].append({'params': [1, 4], 'type': 'OUT_NEQ'})
        if d_idx in [1,3,4]: 
            d['constraints'][0]={'params': [1, 4], 'type': 'OUT_NEQ'}
        if d_idx==2: 
            d['constraints'][1]={'params': [1, 4], 'type': 'OUT_NEQ'}
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,4]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A3>','<R2>']})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A3>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
    save_file(data, file)


files = ['single_or.json']
for file in files:
    data = load_file(file)
    old_data = copy.deepcopy(data)
    new_data = [] 
    for d_idx in range(0,3):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']='action_' + d['nodes'][1]['type']
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']= 'action_' + d['nodes'][3]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>','<A2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
     
    for d_idx in range(3,4):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i1 = tokens.index('<Z4>')
            tokens.insert(i1, '<A4>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']= d['nodes'][2]['type'].replace('relate_', 'relate_action_')
        d['nodes'][5]['side_inputs'].insert(1, '<A4>')
        d['nodes'][5]['type']= d['nodes'][5]['type'].replace('relate_', 'relate_action_')
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A4>'})
        d['constraints'].append({'params': [1, 4], 'type': 'OUT_NEQ'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1,4]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A4>','<R2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    for d_idx in range(4,5):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']= 'action_' + d['nodes'][1]['type']
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']= 'action_' + d['nodes'][3]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>','<A2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    for d_idx in range(5,6):
        old_d = old_data[d_idx]
        old_d['interval_type'] = 'none'
        display_template(d_idx, old_d)
        new_data.append(old_d) 
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(0, '<A>')
        d['nodes'][2]['type']= 'action_' + d['nodes'][2]['type']
        d['nodes'][3]['side_inputs'].insert(0, '<A2>')
        d['nodes'][3]['type']= 'action_' + d['nodes'][3]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>','<A2>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 

    for d_idx in range(6,7):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z2>')
            tokens.insert(i1, '<A2>')
            i1 = tokens.index('<Z3>')
            tokens.insert(i1, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][2]['side_inputs'].insert(1, '<A2>')
        d['nodes'][2]['type']= d['nodes'][2]['type'].replace('relate_', 'relate_action_')
        d['nodes'][4]['side_inputs'].insert(0, '<A3>')
        d['nodes'][4]['type']= 'action_' + d['nodes'][4]['type']
        d['params'].append({'type': 'Action', 'name': '<A2>'})
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [1]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A2>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d) 
    
    for d_idx in range(7,8):
        d = data[d_idx]
        for idx, q in enumerate(d['text']):
            tokens = q.split()
            i1 = tokens.index('<Z>')
            tokens.insert(i1, '<A>')
            i1 = tokens.index('<Z3>')
            tokens.insert(i1, '<A3>')
            d['text'][idx] = ' '.join(tokens) 
        d['nodes'][4]['side_inputs'].insert(1, '<A3>')
        d['nodes'][4]['type']= d['nodes'][4]['type'].replace('relate_', 'relate_action_')
        d['nodes'][1]['side_inputs'].insert(0, '<A>')
        d['nodes'][1]['type']= 'action_' + d['nodes'][1]['type']
        d['params'].append({'type': 'Action', 'name': '<A>'})
        d['params'].append({'type': 'Action', 'name': '<A3>'})
        d['constraints'].append({'type': 'STATIC_ACT', 'params': [3]})
        d['constraints'].append({'type': 'CONTAIN_ACT', 'params': ['<A3>','<R>']})
        d['interval_type'] = 'atomic'
        display_template(d_idx, d)
        new_data.append(d)
        
    save_file(new_data, file)
