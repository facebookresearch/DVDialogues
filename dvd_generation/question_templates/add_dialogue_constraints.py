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

def display_template(file, idx, t):
    print('==========={} {}========='.format(file, idx))
    print(t['text']) 
    
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print('Constraint: {}'.format(t['constraints']))
    print('Interval type {}'.format(t['interval_type']))
    if 'unique_obj' in t: print('Unique obj {}'.format(t['unique_obj']))
    if 'answer_obj' in t: print('Answer obj {}'.format(t['answer_obj']))
    if 'all_unique_objs' in t: print('All unique obj {}'.format(t['all_unique_objs']))
    if 'ref_remark' in t: print('Ref Remark: {}'.format(t['ref_remark']))
    if 'remark' in t: print('Ref: {}'.format(t['remark']))
        
def load_file(file):
    print("Loading template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(data, file):
    new_file = file.replace('_4.json', '_5.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)
    
def save_file2(data, file):
    new_file = file.replace('_5.json', '_5.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)
    
def count_unique(d):
    count = 0 
    for n in d['nodes']:
        if 'unique' in n['type']:
            count += 1
    return count

def get_unique_obj(d):
    for idx, n in enumerate(d['nodes']):
        if 'unique' in n['type']:
            return (idx,n)
        
def get_unique_output_obj(d, last_node_only=True):
    for idx, n in enumerate(d['nodes']):
        if last_node_only and idx!= len(d['nodes'])-1:
            continue 
        if 'filter_count' in n['type']:
            return (idx, n)
        if 'filter_exist' in n['type']:
            return (idx, n)
        if n['type'] == 'exist':
            return (idx, n)
        if n['type'] == 'count':
            return (idx, n)
    return None 

def same_relate_obj(idx, nodes):
    return idx>0 and 'same_' in nodes[idx-1]['type'] and 'query_' in nodes[idx+1]['type']

def spatial_relate_obj(node):
    return  node['type'] == 'relate_action_filter_unique'

def get_all_unique_objs(d, multi_objs=False):
    out = []
    for idx, n in enumerate(d['nodes']):
        if 'unique' in n['type']: # and 'relate' not in n['type']:
            if multi_objs:
                if same_relate_obj(idx, d['nodes']) or spatial_relate_obj(n):
                    out.append((idx, n, 'ans'))
                else:
                    out.append((idx, n, None))
            else:
                out.append((idx, n))
    return out 

def is_exist(d):
    return 'exist' in d['nodes'][-1]['type']

total_templates = 0
unique_temporal_constraint = {'params': [], 'type': 'UNIQUE_NEQ'}
for file in ['zero_hop_4.json', 'compare_integer_4.json', 'comparison_4.json', 'one_hop_4.json',
             'same_relate_4.json']:
    data = load_file(file)
    print("Original # templates: {}".format(len(data)))
    temporal_count = 0 
    new_data = []
    for d_idx in range(len(data)):
        d = data[d_idx]   
        found = False
        
        # Trimming templates that includes spatial relation in these question types 
        if file!='one_hop_4.json' and '<R>' in d['text'][0]: continue 
        # Trimming templates that are not action-related in these question types  
        if file in ['same_relate_4.json', 'comparison_4.json'] \
            and ('same set of activities' not in d['text'][0] \
            and 'same sequence of activities' not in d['text'][0]):
            continue   
        
        uniques = get_all_unique_objs(d)
        if len(uniques)!=0:
            output_idx = [u[0] for u in uniques]
            new_constraint = copy.deepcopy(unique_temporal_constraint)
            new_constraint['params'] = output_idx
            d['constraints'].append(new_constraint)
        # Trimming templates in these question types   
        if file in ['compare_integer_4.json']:
            # Remove templates that does not have a unique entities 
            if len(uniques)!=0:
                found = True 
        elif file in ['same_relate_4.json']:
            # Remove templates that are not temporally dependent 
            if d['interval_type']!='none':
                found = True
        else:
            found = True
        if found:
            new_data.append(d)
            if d['interval_type']!='none':
                temporal_count += 1 
        #display_template(file, d_idx, d)
    save_file(new_data, file)
    print("Original # templates: {}".format(len(data)))
    print("New # templates: {}".format(len(new_data)))
    print("New # temporal templates: {}".format(temporal_count))
    total_templates += len(new_data)
print("Total # new templates: {}".format(total_templates))


for file in ['zero_hop_5.json', 'compare_integer_5.json', 'comparison_5.json','one_hop_5.json',
            'same_relate_5.json']:
    data = load_file(file)
    new_data = []
    unique_obj_template_count = 0
    multiple_objs_template_count = 0
    no_ref_template_count = 0
    ans_obj_template_count = 0
    
    for d_idx in range(len(data)):
        d = data[d_idx]   
        
        if file in ['same_relate_5.json', 'one_hop_5.json']:
            d['all_unique_objs'] = get_all_unique_objs(d, True)
        else:
            d['all_unique_objs'] = get_all_unique_objs(d)
        if len(d['all_unique_objs'])>0:
            multiple_objs_template_count += 1 
        d['answer_obj'] = get_unique_output_obj(d, True) 
        if d['answer_obj'] is not None:
            ans_obj_template_count += 1 
        
        # Remove ambiguous exist text for unique text references 
        new_text = []
        for t in d['text']:
            # remove this as the text do not support object reference
            if 'there is a' in t or 'There is a' in t:
                continue
            # remove this as object containment is involved 
            if 'visible' in t:
                continue 
            # remove template with language that might be off 
            if 'has what' in t or 'is what' in t:
                continue 
            for obj in d['all_unique_objs']:
                unique_text = ' the ' + ' '.join(obj[1]['side_inputs'])
                if unique_text + 's' in t:
                    t = t.replace(unique_text+'s', unique_text)
            # remove ambiguous text 
            if is_exist(d): 
                if file!='one_hop_5.json': 
                    t = t.replace('Are', 'Is').replace('<S>s', '<S>')
                else:
                    t = t.replace('Are', 'Is').replace('<S2>s', '<S2>')
            # grammar errors
            #t = t.replace('Do the', 'Does the')
            new_text.append(t)
        d['text'] = new_text

        # template with action as attributes cannot have references as it is temporally dependent 
        d['ref_remark'] = 'none'
        if '<A> <Z>' in d['text'][0] or 'at least once' in d['text'][0]:
            #and ('<A2>' not in d['text'][0] and '<R' not in d['text'][0]):
            #print("No ref template: {}".format(d['text'][0]))
            d['ref_remark'] = 'no_reference'
            no_ref_template_count += 1 
        
        d['unique_obj'] = None
        if count_unique(d)==1:
            d['unique_obj'] = get_unique_obj(d)
            unique_obj_template_count +=1
                
        #if file in ['same_relate_5.json', 'one_hop_5.json']:
        #    display_template(file, d_idx, d)
        #    pdb.set_trace()
        new_data.append(d)
        
    save_file2(new_data, file)
    
    print("# All template {}".format(len(data)))
    print("# All new template {}".format(len(new_data)))
    print("# Template with single unique obj {}".format(unique_obj_template_count))
    print("# Template with multiple unique objs {}".format(multiple_objs_template_count))
    print("# Template that cannot have reference {}".format(no_ref_template_count))
    print("# Template with answer unique obj (count/exist) {}".format(ans_obj_template_count))
    

constraint = {'type': 'NOT_CONTAIN_ACT', 'params': ['<A2>','<A>']}
for file in ['compare_integer_5.json', 'zero_hop_5.json']:
    data = load_file(file)
    for d_idx in range(len(data)):
        if file == 'zero_hop_5.json' and d_idx !=18: continue
        d = data[d_idx]   
        d['constraints'].append(constraint)
        #display_template(file, d_idx, d)
    save_file2(data, file)
