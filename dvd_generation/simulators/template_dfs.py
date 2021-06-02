"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

from utils.utils import *
from filters.scene_filters import get_filter_options
from filters.constraint_filters import constraint_filters
from simulators.question_generator import instantiate_questions
from utils.global_vars import *
from utils.dialogue_utils import update_unique_object

import simulators.question_engine as qeng
import copy

special_nodes = {
    'filter_unique',
    'filter_count',
    'filter_exist',
    'filter',
    'relate_filter',
    'relate_filter_unique',
    'relate_filter_count',
    'relate_filter_exist',
    'action_filter_count',
    'action_filter_unique',
    'action_filter_exist',
    'relate_action_filter_count', 
    'relate_action_filter_unique',
    'relate_action_filter_exist',
    'action_filter',
    'relate_action_filter',
    'actions_filter_count',
    'actions_filter_exist',
    'actions_filter_unique',
    'actions_filter'
}

def transfer_relate(scene_struct,template,metadata,
                      synonyms, period_idx, turn_dependencies,
                      last_state):
    curr_state = copy.deepcopy(last_state)
    found_relate = False 
    relate_idx = -1 
    for n_idx, n in enumerate(curr_state['nodes']):
        if n['type'] == 'relate':
            found_relate = True 
            relate_idx = n_idx
            n['side_inputs'] = [turn_dependencies['spatial']]
        if found_relate:
            del n['_output'] 
    assert type(curr_state['nodes'][relate_idx-1]['_output']) == int
    curr_state['nodes'][relate_idx-1]['type'] = 'unique_obj_ref'
    curr_state['nodes'][relate_idx-1]['side_inputs'] = 'it'
    for n_idx in range(relate_idx-2,0,-1):
        if curr_state['nodes'][n_idx]['type'] == 'identity': continue 
        if 'filter' not in curr_state['nodes'][n_idx]['type']: pdb.set_trace()
        curr_state['nodes'][n_idx]['type'] = 'identity'
        curr_state['nodes'][n_idx]['inputs'] = [0]
        curr_state['nodes'][n_idx]['_output'] = curr_state['nodes'][0]['_output']
        del curr_state['nodes'][n_idx]['side_inputs']
    curr_state['vals']['<R>'] = turn_dependencies['spatial']
        
    q = {'nodes': curr_state['nodes']}
    outputs = qeng.answer_question(q, metadata, scene_struct, period_idx, turn_dependencies, all_outputs=True)
    answer = outputs[-1]
    if answer == '__INVALID__': 
        pdb.set_trace()

    #answer_counts[answer] += 1
    curr_state['answer'] = answer
    final_states = [curr_state]
    
    return final_states, instantiate_questions(final_states, template, synonyms, scene_struct, period_idx, 
                                               turn_dependencies)
            
    
def transfer_object(scene_struct,template,metadata,
                      synonyms, turn_dependencies,
                      last_state):
    curr_state = copy.deepcopy(last_state)
    curr_state['nodes'] = curr_state['nodes'][-2:]
    curr_state['nodes'][0]['type'] = 'unique_obj_ref'
    curr_state['nodes'][0]['inputs'] = []
    curr_state['nodes'][0]['side_inputs'] = ['its']
    curr_state['nodes'][1]['inputs'] = [0]
    curr_state['nodes'][1]['type'] = turn_dependencies['attribute']
    del curr_state['nodes'][1]['_output'] 
    curr_state['vals'] = {}
    curr_state['input_map'] = {0:0, 1:1}
    curr_state['next_template_node'] = 2

    q = {'nodes': curr_state['nodes']}
    outputs = qeng.answer_question(q, metadata, scene_struct, -1, turn_dependencies, all_outputs=True)
    answer = outputs[-1]
    if answer == '__INVALID__': 
        pdb.set_trace()

    #answer_counts[answer] += 1
    curr_state['answer'] = answer
    final_states = [curr_state]
        
    return final_states, instantiate_questions(final_states, template, synonyms, scene_struct, -1, 
                                               turn_dependencies)
    
def transfer_template(scene_struct,template,metadata,
                      answer_counts, synonyms,period_idx,turn_dependencies,
                      last_state):    
    curr_state = copy.deepcopy(last_state)
    
    for n in curr_state['nodes']:
        if n['type'] in ['earlier_obj_ref', 'unique_obj_ref']: continue
        del n['_output'] 
    q = {'nodes': curr_state['nodes']}
    outputs = qeng.answer_question(q, metadata, scene_struct, period_idx, turn_dependencies, all_outputs=True)
    answer = outputs[-1]
    if answer == '__INVALID__': 
        pdb.set_trace()

    answer_counts[answer] += 1
    curr_state['answer'] = answer
    final_states = [curr_state]

    return final_states, instantiate_questions(final_states, template, synonyms, scene_struct, period_idx, 
                                               turn_dependencies)

def instantiate_templates_dfs(scene_struct, template, metadata,
                              answer_counts, synonyms, period_idx, turn_dependencies,
                              max_instances=None, turn_pos=-1, verbose=False):

    param_name_to_type = {p['name']: p['type'] for p in template['params']}
    
    curr_period = template['used_periods'][-1]
    cutoff = template['cutoff']

    initial_state = {
        'nodes': [node_shallow_copy(template['nodes'][0])],
        'vals': {},
        'input_map': {0: 0},
        'next_template_node': 1,
    }
    states = [initial_state]
    final_states = []
    while states:
        state = states.pop()

        # Check to make sure the current state is valid
        q = {'nodes': state['nodes']}
        outputs = qeng.answer_question(q, metadata, scene_struct, period_idx, turn_dependencies, all_outputs=True)
        answer = outputs[-1]
        if answer == '__INVALID__': continue

        # Check to make sure constraints are satisfied for the current state
        skip_state = constraint_filters(scene_struct, template, param_name_to_type, state, outputs, 
                                        period_idx, turn_dependencies=turn_dependencies, verbose=False)
        if skip_state: continue

        # We have already checked to make sure the answer is valid, so if we have
        # processed all the nodes in the template then the current state is a valid
        # question, so add it if it passes our rejection sampling tests.
        if state['next_template_node'] == len(template['nodes']):
            skip_by_sampling_check = sample_question_by_answer_counts(answer_counts, answer, verbose)
            if skip_by_sampling_check: continue 
            
            # If the template contains a raw relate node then we need to check for
            # degeneracy at the end
            has_relate = any(n['type'] == 'relate' for n in template['nodes'])
            if has_relate:
                degen = qeng.is_degenerate(q, metadata, scene_struct, answer=answer, period_idx=period_idx, verbose=verbose)
                if degen: continue

            answer_counts[answer] += 1
            state['answer'] = answer

            final_states.append(state)
            if max_instances is not None and len(final_states) == max_instances: break
            pdb.set_trace()
            continue
            
        # Otherwise fetch the next node from the template
        # Make a shallow copy so cached _outputs don't leak ... this is very nasty
        next_node = template['nodes'][state['next_template_node']]
        next_node = node_shallow_copy(next_node)

        if next_node['type'] in special_nodes:
            
            if random.random()>0 and 'unique' in next_node['type'] \
                and template['prior_unique_obj'] != -1 \
                and template['unique_obj'] is not None \
                and (template['interval_type'] == 'none' \
                     or 'none' not in turn_dependencies['temporal'] \
                     or curr_period==(None, cutoff)) \
                and template['ref_remark'] != 'no_reference': 
                input_map = {k: v for k, v in state['input_map'].items()}
                cur_next_vals = {k: v for k, v in state['vals'].items()}
                new_nodes = []
                new_nodes.append({
                    'type': 'unique_obj_ref',
                    'inputs':[input_map[next_node['inputs'][0]] + len(new_nodes)],
                    '_output': template['prior_unique_obj']
                })
                
                input_map[state['next_template_node']] = len(state['nodes']) + len(new_nodes) - 1
                for k,v in template['prior_unique_obj_attr'].items():
                    # only save old action value if same period
                    if '<A' in k:
                        curr_period = template['used_periods'][-1]
                        if v['period'] == curr_period: 
                            cur_next_vals[k] = v['val']
                        continue
                    cur_next_vals[k] = v
                states.append({
                    'nodes':state['nodes'] + new_nodes,
                    'vals': cur_next_vals,
                    'input_map':input_map,
                    'next_template_node':state['next_template_node'] + 1,
                })
                turn_dependencies['object'] = 'last_unique' 
                
                if template['sampled_ans_object']!=-1: 
                    oa = template['sampled_ans_object_attr_ref']
                    oi = template['sampled_ans_object'] 
                    update_unique_object(oi, oa, template['used_objects'], turn_pos)
                
                continue 

            if  random.random()>0 and 'unique' in next_node['type'] \
                and template['earlier_unique_obj']!=-1 \
                and template['earlier_unique_obj_node']==next_node:
                input_map = {k: v for k, v in state['input_map'].items()}
                cur_next_vals = {k: v for k, v in state['vals'].items()}
                new_nodes = []
                new_nodes.append({
                    'type': 'earlier_obj_ref',
                    'inputs':[input_map[next_node['inputs'][0]] + len(new_nodes)],
                    '_output': template['earlier_unique_obj']
                })
                input_map[state['next_template_node']] = len(state['nodes']) + len(new_nodes) - 1     
                attr_map = template['earlier_unique_obj_attr_map']
                for k,v in template['earlier_unique_obj_attr'].items(): 
                    cur_next_vals[attr_map[k]] = v
                turn_dependencies['object'] = 'earlier_unique'
                states.append({
                    'nodes':state['nodes'] + new_nodes,
                    'vals': cur_next_vals,
                    'input_map':input_map,
                    'next_template_node':state['next_template_node'] + 1,
                })
                continue 
                
            filter_options = get_filter_options(metadata, scene_struct, template, answer, next_node, period_idx)
            filter_option_keys = list(filter_options.keys())
            random.shuffle(filter_option_keys)
            
            for k in filter_option_keys:
                new_nodes = []
                cur_next_vals = {k: v for k, v in state['vals'].items()}
                next_input = state['input_map'][next_node['inputs'][0]]
                filter_side_inputs = next_node['side_inputs']
                if next_node['type'].startswith('relate'):
                    param_name = next_node['side_inputs'][0]  # First one should be relate
                    filter_side_inputs = next_node['side_inputs'][1:]
                    param_type = param_name_to_type[param_name]
                    assert param_type == 'Relation'
                    param_val = k[0]
                    k = k[1]
                    new_nodes.append({
                        'type': 'relate',
                        'inputs': [next_input],
                        'side_inputs': [param_val],
                    })
                    cur_next_vals[param_name] = param_val
                    next_input = len(state['nodes']) + len(new_nodes) - 1
                for param_name, param_val in zip(filter_side_inputs, k):
                    param_type = param_name_to_type[param_name]
                    if param_type == 'Action' and 'actions' in next_node['type']: 
                        filter_type = 'filter_actions'
                    else:
                        filter_type = 'filter_%s' % param_type.lower()
                    if param_val is not None:
                        new_nodes.append({
                            'type': filter_type,
                            'inputs': [next_input],
                            'side_inputs': [param_val],
                        })
                        cur_next_vals[param_name] = param_val
                        next_input = len(state['nodes']) + len(new_nodes) - 1
                    elif param_val is None:
                        if metadata['dataset'] == 'CLEVR-v1.0' and param_type == 'Shape':
                            param_val = 'thing'
                        else:
                            param_val = ''
                        cur_next_vals[param_name] = param_val
                input_map = {k: v for k, v in state['input_map'].items()}
                extra_type = None
                if next_node['type'].endswith('unique'):
                    extra_type = 'unique'
                if next_node['type'].endswith('count'):
                    extra_type = 'count'
                if next_node['type'].endswith('exist'):
                    extra_type = 'exist'
                if extra_type is not None:
                    new_nodes.append({
                        'type':extra_type,
                        'inputs':[input_map[next_node['inputs'][0]] + len(new_nodes)],
                    })
                input_map[state['next_template_node']] = len(
                    state['nodes']) + len(new_nodes) - 1
                states.append({
                    'nodes':state['nodes'] + new_nodes,
                    'vals':cur_next_vals,
                    'input_map':input_map,
                    'next_template_node':state['next_template_node'] + 1,
                })
        # i.e. 'Relate' node 
        elif 'side_inputs' in next_node:
            # If the next node has template parameters, expand them out
            # TODO: Generalize this to work for nodes with more than one side input
            assert len(next_node['side_inputs']) == 1, 'NOT IMPLEMENTED: {}'.format(next_node)

            # Use metadata to figure out domain of valid values for this parameter.
            # Iterate over the values in a random order; then it is safe to bail
            # from the DFS as soon as we find the desired number of valid template
            # instantiations.
            param_name = next_node['side_inputs'][0]
            if param_name not in param_name_to_type: 
                print(template)
                pdb.set_trace()
            param_type = param_name_to_type[param_name]
            param_vals = metadata['types'][param_type][:]
            random.shuffle(param_vals)
            for val in param_vals:
                input_map = {k: v for k, v in state['input_map'].items()}
                input_map[state['next_template_node']] = len(state['nodes'])
                cur_next_node = {
                    'type': next_node['type'],
                    'inputs': [input_map[idx] for idx in next_node['inputs']],
                    'side_inputs': [val],
                }
                cur_next_vals = {k: v for k, v in state['vals'].items()}
                cur_next_vals[param_name] = val

                states.append({
                    'nodes':state['nodes'] + [cur_next_node],
                    'vals':cur_next_vals,
                    'input_map':input_map,
                    'next_template_node':state['next_template_node'] + 1,
                })
        # remaining node types: 
        # scene, unique, union, intersect, count, exist, 
        # query_shape, query_color, query_size, query_material
        # equal_color, equal_shape, equal_size, equal_material, 
        # same_size, same_color, same_material, same_shape, 
        # equal_object, equal_integer, less_than, greater_than
        else:
            input_map = {k: v for k, v in state['input_map'].items()}
            input_map[state['next_template_node']] = len(state['nodes'])
            next_node = {
                'type': next_node['type'],
                'inputs': [input_map[idx] for idx in next_node['inputs']],
            }
            states.append({
                'nodes':state['nodes'] + [next_node],
                'vals':state['vals'],
                'input_map':input_map,
                'next_template_node':state['next_template_node'] + 1,
            })

    return final_states, instantiate_questions(final_states, template, synonyms, scene_struct, period_idx, 
                                               turn_dependencies)
