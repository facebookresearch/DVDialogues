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
    Introduce action for query e.g. what actions/set of actions/sequence of actions ... 
    This type of question is for atomic or compositional interval  
    Additional constraint: 
        NOT_NULL_ACT: one of the constraint params need to be a non-empty action 
        NOT_STATIC_ACT: all param must not be stationary  
        STATIC_ACT: the output object of the node (e.g. filter_unique) in constraint params must be stationary/rotating. 
            This is for object used as a base for spatial dependency
        CONTAIN_ACT: param include an action <A> and relation <R>. if relation is 'containing', action only be sliding; if relation is 'contained', action must be empty 
    Additional field in template: 
            interval_type: atomic (each object can have max. 1 action in an atomic interval); 
                           composition (each object can have more than 1 actions per interval)
            action_remark: heuristic rules to instantiate text 
"""

def display_template(idx, t):
    return 
    print('==========={}========='.format(idx))
    print(t['text']) 
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print(t['constraints'])
    print(t['params'])
    if 'interval_type' in t: print(t['interval_type'])
    print()
    pdb.set_trace()
    
def load_file(file):
    file = file.replace('.json', '_2.json')
    print("Adding action query in compositional interval into template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(old_data, data, file):
    data = old_data + data 
    new_file = file.replace('.json', '_3.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)

files = ['compare_integer.json']
for file in files:
    data = load_file(file)
    
    new_data = []    
    for d_idx in [1,3,5]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        display_template(d_idx, d)
        for idx, q in enumerate(new_d['text']):
            q = q.replace('<A> ','').replace('<A2> ','').replace('?','')
            tokens = q.split()
            i1 = tokens.index('<S>s')
            tokens.insert(i1+1, 'that <A> at least once')
            i2 = tokens.index('<S2>s')
            tokens.insert(i2+1, 'that <A2> at least once?')
            new_d['text'][idx] = ' '.join(tokens)
        new_d['nodes'][1]['type']='actions_filter_count'
        new_d['nodes'][3]['type']='actions_filter_count'
        new_d['constraints'].append({'type': 'NOT_STATIC_ACT', 'params': ['<A2>', '<A>']})
        new_d['interval_type'] = 'compositional'
        # ad-hoc remark for replacing action to verbs e.g. sliding --> slide 
        new_d['remark'] = 'action_verb'
        new_data.append(new_d)
        display_template(d_idx, new_d)

        new_d = copy.deepcopy(d)
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('?','')
            tokens = q.split()
            i1 = tokens.index('<A>')
            tokens.insert(i1+1, 'actions that the')
            i2 = tokens.index('<A2>')
            tokens.insert(i2+1, 'actions that the')
            i1 = tokens.index('<S>s')
            tokens[i1] = '<S> performs'
            i2 = tokens.index('<S2>s')
            tokens[i2] = '<S2> performs?'
            new_d['text'][idx] = ' '.join(tokens)
        '''
        if d_idx==1:
            new_d['text']=[
                #'Does the <Z> <C> <M> <S> <A> for the same number of times as the <Z2> <C2> <M2> <S2> <A2>?',
                'Does the <Z> <C> <M> <S> <A> as frequently as the <Z2> <C2> <M2> <S2> <A2>?']
        if d_idx==3:
            new_d['text']=[
                #'Does the <Z> <C> <M> <S> <A> for a fewer number of times than the <Z2> <C2> <M2> <S2> <A2>?',
                'Does the <Z> <C> <M> <S> <A> less frequently than the <Z2> <C2> <M2> <S2> <A2>?']
        if d_idx==5:
            new_d['text']=[
                #'Does the <Z> <C> <M> <S> <A> for a larger number of times than the <Z2> <C2> <M2> <S2> <A2>?',
                'Does the <Z> <C> <M> <S> <A> more frequently than the <Z2> <C2> <M2> <S2> <A2>?']
        
        
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'].insert(2, {'side_inputs': ['<A>'], 
                                  'inputs': [1], 'type': 'action_count'})
        new_d['nodes'][4]['type']='filter_unique'
        new_d['nodes'][4]['side_inputs'].pop(0)
        new_d['nodes'][4]['inputs']=[3]
        new_d['nodes'].insert(5, {'side_inputs': ['<A2>'], 
                                  'inputs': [4], 'type': 'action_count'})
        new_d['nodes'][6]['inputs']=[2,5]
        new_d['constraints']=[{'params': [1, 4], 'type': 'OUT_NEQ'}, 
                              {'type': 'NOT_STATIC_ACT', 'params': ['<A2>', '<A>']},
                             {'type': 'NOT_NULL_ACT', 'params': ['<A2>']}, {'type': 'NOT_NULL_ACT', 'params': ['<A>']}]
        new_d['interval_type'] = 'compositional'
        new_d['action_remark'] = {'<A>': 'action_verb', '<A2>': 'action_verb_singular'}
        display_template(d_idx, new_d)
        new_data.append(new_d)
    save_file(data, new_data, file)

files = ['comparison.json']
for file in files:
    data = load_file(file)
    new_data = []
    for d_idx in [1]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        display_template(d_idx, d)
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'set of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        '''
        new_d['text']=[
            'Do the <Z> <C> <M> <S> and the <Z2> <C2> <M2> <S2> perform the same set of activities?', 
            'Do the <Z> <C> <M> <S> and the <Z2> <C2> <M2> <S2> undertake the same types of actions?', 
            'Does the <Z> <C> <M> <S> perform the same set of activities as the <Z2> <C2> <M2> <S2>?',
            'Does the <Z> <C> <M> <S> undertake the same types of actions as the <Z2> <C2> <M2> <S2>?']
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][3]['type']='filter_unique'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['nodes'][4] = { 'inputs': [1], 'type': 'query_action_set'}
        new_d['nodes'][5] = {'inputs': [3], 'type': 'query_action_set'}
        new_d['nodes'][6]['type'] = 'equal_action'
        new_d['constraints'] = [{'params': [1, 3], 'type': 'OUT_NEQ'}]
        #{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']], 
        #            [3, ['<Z2>', '<C2>', '<M2>', '<S2>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
        new_d = copy.deepcopy(d)
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'sequence of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        '''
        new_d['text']=[
            'Do the <Z> <C> <M> <S> and the <Z2> <C2> <M2> <S2> perform the same sequence of activities?', 
            'Does the <Z> <C> <M> <S> perform the same sequence of activities as the <Z2> <C2> <M2> <S2>?']      
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][3]['type']='filter_unique'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['nodes'][4] = { 'inputs': [1], 'type': 'query_action_seq'}
        new_d['nodes'][5] = {'inputs': [3], 'type': 'query_action_seq'}
        new_d['nodes'][6]['type'] = 'equal_action'
        new_d['constraints'] = [{'params': [1, 3], 'type': 'OUT_NEQ'}]
        #{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']], 
        #            [3, ['<Z2>', '<C2>', '<M2>', '<S2>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
    save_file(data, new_data, file)

files = ['same_relate.json']
for file in files:
    data = load_file(file)
    new_data = []
    
    
    for d_idx in [1,9]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        display_template(d_idx, d)
        
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'set of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        '''
        if d_idx == 1:
            new_d['text']=[
             'Is there anything else that performs the same set of activities as the <Z> <C> <M> <S>?', 
             'Is there any other thing that has the same types of actions as the <Z> <C> <M> <S>?',
             'Is there any other thing with the same set of activities performed by the <Z> <C> <M> <S>?',
             'Is there any other object that has the same types of actions as the <Z> <C> <M> <S>?',
             'Is there any other object with the same set of activities performed by the <Z> <C> <M> <S>?']
        if d_idx == 9:
            new_d['text']=[
                'How many other things perform the same set of activities as the <Z> <C> <M> <S>?', 
                'How many other things undertake the same types of actions as the <Z> <C> <M> <S>?', 
                'How many other things with the same set of activities performed by the <Z> <C> <M> <S>?', 
                'How many other objects perform the same set of activities as the <Z> <C> <M> <S>?', 
                'How many other objects undertake the same types of actions as the <Z> <C> <M> <S>?', 
                'How many other objects with the same set of activities performed by the <Z> <C> <M> <S>?']
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_set'}
        new_d['constraints'] = [] #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
        new_d = copy.deepcopy(d)
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'sequence of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        '''
        if d_idx == 1:
            new_d['text']=[
             'Is there anything else that performs the same sequence of activities as the <Z> <C> <M> <S>?', 
             'Is there any other thing with the same sequence of activities performed by the <Z> <C> <M> <S>?',
             'Is there any other object with the same sequence of activities performed by the <Z> <C> <M> <S>?']
        if d_idx == 9:
            new_d['text']=[
                'How many other things perform the same sequence of activities as the <Z> <C> <M> <S>?', 
                'How many other things with the same sequence activities performed by the <Z> <C> <M> <S>?', 
                'How many other objects perform the same sequence of activities as the <Z> <C> <M> <S>?', 
                'How many other objects with the same sequence of activities performed by the <Z> <C> <M> <S>?']
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_seq'}
        new_d['constraints'] = [] #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
    
    for d_idx in [17]:        
        d = data[d_idx]
        
        new_d = copy.deepcopy(d)
        display_template(d_idx, d)
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'set of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_set'}
        new_d['nodes'][3]['type']='filter_exist'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['constraints'] = [] # [{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'sequence of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_seq'}
        new_d['nodes'][3]['type']='filter_exist'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['constraints'] = [] #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
    for d_idx in [25]:
        d = data[d_idx]
        display_template(d_idx, d)
        
        new_d = copy.deepcopy(d)    
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'set of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_set'}
        new_d['nodes'][3]['type']='filter_count'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['constraints'] = [] #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
        new_d = copy.deepcopy(d)    
        for idx, q in enumerate(new_d['text']):
            q = q.replace('size', 'sequence of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][2] = { 'inputs': [1], 'type': 'same_action_seq'}
        new_d['nodes'][3]['type']='filter_count'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['constraints'] = [] #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
    
    for d_idx in [33,39,45,51]:        
        d = data[d_idx]
        display_template(d_idx, d)
                
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            if d_idx == 33: 
                q = q.replace('color', 'set of actions')
            else:
                q = q.replace('size', 'set of actions')
            q = q.replace('<A>', '')
            q = q.replace('<A2>', '')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][3]['type']='filter_unique'
        new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['nodes'][4] = { 'inputs': [3], 'type': 'query_action_set'}
        new_d['constraints'] = new_d['constraints'][:2] #+ \
                                #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']], 
                                #            [3, ['<Z2>', '<C2>', '<M2>', '<S2>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
    for d_idx in [32,34,36,38]:        
        d = data[d_idx]
        display_template(d_idx, d)
                        
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            if d_idx == 38: 
                q = q.replace('color', 'set of actions')
            else:
                q = q.replace('size', 'set of actions')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        #new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][3]['type']='filter_unique'
        #new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['nodes'][2]['type'] = 'same_action_set'
        new_d['constraints'] = new_d['constraints'][-1:] #+ \
                                #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']], 
                                #            [3, ['<Z2>', '<C2>', '<M2>', '<S2>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            if d_idx == 38: 
                q = q.replace('color', 'sequence of actions')
            else:
                q = q.replace('size', 'sequence of actions')
            q = ' '.join(q.split())
            new_d['text'][idx] = q
        new_d['nodes'][1]['type']='filter_unique'
        #new_d['nodes'][1]['side_inputs'].pop(0)
        new_d['nodes'][3]['type']='filter_unique'
        #new_d['nodes'][3]['side_inputs'].pop(0)
        new_d['nodes'][2]['type'] = 'same_action_seq'
        new_d['constraints'] = new_d['constraints'][-1:] #+ \
                                #[{'params': [[1, ['<Z>', '<C>', '<M>', '<S>']], 
                                #            [3, ['<Z2>', '<C2>', '<M2>', '<S2>']]], 'type': 'MINIMAL_ATTR'}]
        new_d['interval_type'] = 'compositional'
        new_data.append(new_d)
        display_template(d_idx, new_d)
        
    save_file(data, new_data, file)

files = ['zero_hop.json']
for file in files:
    data = load_file(file)
    new_data=[]
    
    for d_idx in [0,2,4,6,8,10]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        '''
        for idx, q in enumerate(new_d['text']):
            q = q.replace('?','')
            tokens = q.split()
            temp = False
            if '<S>s' in tokens:
                i1 = tokens.index('<S>s')
            elif '<S>' in tokens:
                i1 = tokens.index('<S>') 
            else:
                i1 = tokens.index('<S>;') 
                temp = True
            if temp:
                tokens[i1] = '<S> that <A> at least once;'
            else:
                tokens.insert(i1+1, 'that <A> at least once')
            new_d['text'][idx] = ' '.join(tokens)+'?'
        '''
        new_d['text'] = copy.deepcopy(data[d_idx+1]['text'])
        new_d['nodes'][1]['side_inputs'].insert(0, '<A>')
        new_d['nodes'][1]['type']='actions_' + new_d['nodes'][1]['type']
        new_d['params'].append({'type': 'Action', 'name': '<A>'})
        new_d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>']})
        new_d['constraints'].append({'type': 'NOT_STATIC_ACT', 'params': ['<A>']})
        new_d['interval_type'] = 'compositional'
        #new_d['action_remark'] = {'<A>': 'action_verb_singular'}
        display_template(d_idx, new_d)
        new_data.append(new_d) 
       
    for d_idx in [0]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] =  ['How many times does the <Z> <C> <M> <S>s <A>?', 
                          'How many times does the <Z> <C> <M> <S>s <A> in total?']
        
        new_d['nodes'][1]['type']='filter_unique'
        new_d['nodes'].append({'side_inputs': ['<A>'], 'inputs': [1], 'type': 'action_count'})
        new_d['params'].append({'type': 'Action', 'name': '<A>'})
        new_d['constraints'].append({'type': 'NOT_NULL_ACT', 'params': ['<A>']})
        new_d['constraints'].append({'type': 'NOT_STATIC_ACT', 'params': ['<A>']})
        new_d['interval_type'] = 'compositional'
        new_d['action_remark'] = {'<A>': 'action_verb'}
        display_template(d_idx, new_d)
        new_data.append(new_d) 
        
    for d_idx in [10]:
        d = data[d_idx]
        new_d = copy.deepcopy(d)
        new_d['text'] = ['What types of actions does the <Z> <C> <M> <S> undertake?', 
                         'What are the activities that the <Z> <C> <M> <S> perform?',
                         'What is the <Z> <C> <M> <S> doing?']
        
        new_d['nodes'][2]['type']='query_action_set'
        new_d['constraints'] = []
        new_d['interval_type'] = 'compositional'
        display_template(d_idx, new_d)
        new_data.append(new_d) 
        
    save_file(data, new_data, file)
    

files = ['one_hop.json', 'two_hop.json', 'three_hop.json', 'single_and.json']
for file in files:
    data = load_file(file)
    new_data = [] 
    save_file(data, new_data, file)

files = ['single_or.json']
for file in files:
    data = load_file(file)
    new_data = [] 
    for d_idx in [1,3,5,8]:
        d = data[d_idx]
        display_template(d_idx, d)
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            q = q.replace('?','').replace('<A>','').replace('<A2>','')
            tokens = q.split()
            i1 = tokens.index('<S>s')
            tokens.insert(i1+1, 'that <A> at least once')
            i1 = tokens.index('<S2>s')
            tokens.insert(i1+1, 'that <A2> at least once')
            new_d['text'][idx] = ' '.join(tokens) + '?'
        new_d['nodes'][1]['type']='actions_filter'
        new_d['nodes'][3]['type']= 'actions_filter' 
        new_d['params'].append({'type': 'Action', 'name': '<A>'})
        new_d['params'].append({'type': 'Action', 'name': '<A2>'})
        new_d['constraints'].append({'type': 'NOT_STATIC_ACT', 'params': ['<A>','<A2>']})
        new_d['interval_type'] = 'compositional'
        new_d['remark'] = 'action_verb'
        display_template(d_idx, new_d)
        new_data.append(new_d) 
        
    for d_idx in [10]:
        d = data[d_idx]
        display_template(d_idx, d)
        new_d = copy.deepcopy(d)
        for idx, q in enumerate(new_d['text']):
            q = q.replace('?','').replace('<A>','').replace('<A2>','')
            tokens = q.split()
            i1 = tokens.index('<S>s')
            tokens.insert(i1+1, 'that <A> at least once')
            i1 = tokens.index('<S2>s')
            tokens.insert(i1+1, 'that <A2> at least once')
            new_d['text'][idx] = ' '.join(tokens) + '?'
        new_d['nodes'][2]['type']='actions_filter'
        new_d['nodes'][3]['type']= 'actions_filter' 
        new_d['params'].append({'type': 'Action', 'name': '<A>'})
        new_d['params'].append({'type': 'Action', 'name': '<A2>'})
        new_d['constraints'].append({'type': 'NOT_STATIC_ACT', 'params': ['<A>','<A2>']})
        new_d['interval_type'] = 'compositional'
        new_d['remark'] = 'action_verb'
        display_template(d_idx, new_d)
        new_data.append(new_d) 
    save_file(data, new_data, file)
    

    
