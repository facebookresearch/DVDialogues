"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

from utils.utils import *
from utils.scene_utils import is_static_or_rotating, get_identifier, convert_to_compositional_period_idx
from utils.global_vars import *
from simulators.question_engine import update_state

# Ensure that all unique objects in a question sentence are unique, including objects that 
# are mentioned in temporal localization 
def unique_neq_filter(scene_struct, template, constraint, param_name_to_type, 
                      state, outputs, period_idx, period_relation=None, verbose=False):
    vals = []
    for param in constraint['params']:
        param = state['input_map'].get(param, None)
        if param is not None:
            val = outputs[param]
            vals.append(val) 
        else:
            return False
    if template['interval_type']!='none':
        e1, e2 = scene_struct[intervals_to_periods[template['interval_type']]][period_idx]
        if e1 is not None and e2 is not None: 
            if e1[0] == e2[0]:
                vals.append(e1[0])
            else:
                vals.append(e1[0])
                vals.append(e2[0])
        elif e1 is not None:
            vals.append(e1[0])
        elif e2 is not None: 
            vals.append(e2[0])
    #print(vals, state, state['input_map'], constraint)
    if len(set(vals)) < len(vals): 
        if verbose:
            print('skipping due to UNIQUE_NEQ constraint')
            print(constraint['params'])
            print(vals)
        return True
    return False 

def static_action_filter(scene_struct, template, constraint, param_name_to_type, 
                         state, outputs, period_idx, period_relation=None, verbose=False):
    ps = constraint['params']
    skip = False
    for p in ps: 
        i = state['input_map'].get(p, None)
        if i is not None:
            obj_idx = outputs[i]
            assert type(obj_idx) == int 
            if not is_static_or_rotating(scene_struct, template, period_idx, obj_idx): 
                skip = True 
                break
    if skip:
        if verbose:
            print('skipping due to STATIC_ACT constraint')
            print(constraint) 
            print(obj_idx)
        return True
    return False 

def minimal_action_attribute_filter(scene_struct, template, constraint, param_name_to_type, 
                                    state, outputs, period_idx, period_relation='during', verbose=False):
    if template['interval_type'] == 'atomic':
        new_period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
    else:
        new_period_idx = period_idx 
        #identifiers = scene_struct['_minimal_object_identifiers_with_action'][period_idx]
    #elif template['interval_type'] == 'compositional':
    identifiers = scene_struct['_minimal_object_identifiers_with_actions'][new_period_idx][period_relation]
    for node_idx, params in constraint['params']:
        i = state['input_map'].get(node_idx, None)
        if i is not None:
            #prior_i = state['input_map'].get(node_idx-1)
            #old_nodes = state['nodes'][prior_i+1:i]
            output = outputs[i]
            # if object are referred objects, exclude from this constraint 
            if output == template['prior_unique_obj']:
                continue
            if output == template['earlier_unique_obj']:
                continue
            identifier = get_identifier(params, state, param_name_to_type)
            # In case of 2 identical objects in video in the same period, skip
            if identifiers[output] is None:
                return True   
            if identifier in identifiers[output]:
                continue 
            identifier = random.sample(identifiers[output],1)[0]
            update_state(outputs, node_idx, params, param_name_to_type, identifier, state, scene_struct, template, period_idx)            
    return False 

def nonunique_action_attribute_filter(scene_struct, template, constraint, param_name_to_type, 
                                      state, outputs, period_idx, period_relation='during', verbose=False):
    if template['interval_type'] == 'atomic':
        period_idx = convert_to_compositional_period_idx(scene_struct, period_idx) 
        #identifiers = scene_struct['_object_identifiers_with_action']
    #elif template['interval_type'] == 'compositional':
    identifiers = scene_struct['_object_identifiers_with_actions'][period_idx][period_relation]
    for i, params in constraint['params']:
        i = state['input_map'].get(i, None)
        if i is not None:
            output = outputs[i]
            # if object are referred objects, exclude from this constraint 
            if output == template['prior_unique_obj']:
                continue
            if output == template['earlier_unique_obj']:
                #pdb.set_trace()
                #TODO
                continue
            curr_identifier = get_identifier(params, state, param_name_to_type)
            # In case of 2 identical objects in video
            if identifiers[output] is None:
                continue
            # if current identifier can identify unique object, skip
            if curr_identifier in identifiers[output]: 
                return True 
    return False 
