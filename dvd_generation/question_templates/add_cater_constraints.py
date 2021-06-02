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
    TODO: 
    Check OUT_NEQ constraints 
    Check snitch constraints; still errors 
"""
"""
    Introduce additional constraints unique to the CATER videos: 
    'EXC_CONTAINING: excluding 'containing' in <R> params in question querying about shape as the shape of a container 
        is always cone only 
     CONTAIN_SHAPE_SIZE: excluding params to select objects as containers (non-cone objects and or small objects) and containees (large objects); also check for size params that specifies container size < containee size
     MINIMAL_ATTR/MINIMAL_ACT_ATTR: constraints for using minimal attribute combination to uniquely identify an object; this is to reduce redudancy and challenge models to find objects in videos 
"""

FILES = [
    'compare_integer.json', 'comparison.json', 'same_relate.json', 
    'zero_hop.json', 'one_hop.json', 'two_hop.json', 'three_hop.json',
    'single_and.json', 'single_or.json'
]

def display_template(file, idx, t):
    return 
    print('==========={}-{}========='.format(file,idx))
    print(t['text']) 
    for idx, n in enumerate(t['nodes']):
        print(idx, n)
    print(t['constraints'])
    print(t['params'])
    if 'interval_type' in t: print(t['interval_type'])
    print()
    pdb.set_trace()
    
def load_file(file):
    file = file.replace('.json', '_3.json')
    print("Loading template {}...".format(file))
    data = json.load(open(file))
    return data 
    
def save_file(data, file):
    new_file = file.replace('.json', '_4.json')
    print("Writing new template to {}...".format(new_file))
    json.dump(data, open(new_file, 'w'), indent=4)

print('Updating constraints for containment - excluding query shape of container object since it is always a cone...') 
constraint = {'params': [], 'type': 'EXC_CONTAINING'}
for file in FILES:
    data = load_file(file) 
    for idx, d in enumerate(data):
        q = d['text'][0]
        nodes = d['nodes']
        if nodes[-1]['type'] == 'query_shape' and '<R' in q: 
            curr_constraint = copy.deepcopy(constraint)
            if file=='single_and.json':
                curr_constraint['params'].extend(['<R>','<R2>'])
            else:
                last_relation = nodes[-2]['side_inputs'][0]      
                assert '<R' in last_relation
                curr_constraint['params'].append(last_relation)
            d['constraints'].append(curr_constraint)
            display_template(file, idx, d) 
    json.dump(data, open(file, 'w'), indent=4)
    save_file(data, file) 

def same_relate_obj(idx, nodes):
    return idx>0 and 'same_' in nodes[idx-1]['type'] and 'query_' in nodes[idx+1]['type']
    
print("Adding constraint for minimal attribute combination as object identifier")
for file in FILES:
    data = load_file(file)
    for idx, d in enumerate(data): 
        unique_nodes = []
        unique_nodes_action = []
        nonunique_nodes = []
        nonunique_nodes_action = []
        for n_idx, n in enumerate(d['nodes']):
            if 'unique' in n['type']:
                if 'relate' not in n['type']:
                    if n['type'] in ['action_filter_unique']:
                        if 'same_relate' in file:
                            if same_relate_obj(n_idx, d['nodes']):
                                nonunique_nodes_action.append((n_idx,n))
                            else:
                                unique_nodes_action.append((n_idx,n))
                        elif 'single_and' not in file: 
                            unique_nodes_action.append((n_idx,n))
                        else:
                            nonunique_nodes_action.append((n_idx,n))
                    if n['type'] in ['actions_filter_unique']:
                        if 'same_relate' in file:
                            pdb.set_trace()
                        elif 'single_and' not in file: 
                            unique_nodes_action.append((n_idx,n))
                        else:
                            pdb.set_trace()
                    elif n['type'] == 'filter_unique': 
                        if 'same_relate' in file:
                            if same_relate_obj(n_idx, d['nodes']):
                                nonunique_nodes.append((n_idx, n))
                            else:
                                unique_nodes.append((n_idx, n))
                        else:
                            unique_nodes.append((n_idx, n))
                else:
                    if n['type'] == 'relate_action_filter_unique':
                        nonunique_nodes_action.append((n_idx,n))
                    elif n['type'] == 'relate_actions_filter_unique':
                        pdb.set_trace()
                    elif n['type'] == 'relate_filter_unique':
                        nonunique_nodes.append((n_idx, n))
        found = False
        # insert to first position before checking any other constraints 
        if len(unique_nodes)>0: 
            output_nodes = [(i,n['side_inputs'][-4:]) for i,n in unique_nodes]
            d['constraints'].insert(0,{'params': output_nodes, 'type': 'MINIMAL_ATTR'})
            found = True
        if len(unique_nodes_action)>0:
            output_nodes = [(i,n['side_inputs'][-5:])  for i,n in unique_nodes_action]
            d['constraints'].insert(0, {'params': output_nodes, 'type': 'MINIMAL_ACT_ATTR'})               
            found = True
            
        if len(nonunique_nodes)>0: 
            output_nodes = [(i,n['side_inputs'][-4:]) for i,n in nonunique_nodes]
            d['constraints'].insert(0,{'params': output_nodes, 'type': 'NONUNIQUE_ATTR'})
            found = True
        if len(nonunique_nodes_action)>0:
            output_nodes = [(i,n['side_inputs'][-5:])  for i,n in nonunique_nodes_action]
            d['constraints'].insert(0, {'params': output_nodes, 'type': 'NONUNIQUE_ACT_ATTR'})               
            found = True
        if found:
        #if 'single_and' in file:
            display_template(file, idx, d)
    save_file(data, file)  

