"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

from utils.utils import *
from utils.scene_utils import get_identifier
from utils.dialogue_utils import strip_attr_key
from utils.global_vars import *
from simulators.question_engine import update_state

def is_null(v, p_type, verbose=False):
    if v is not None:
        skip = False
        if p_type == 'Shape' and v != 'thing': skip = True
        if p_type != 'Shape' and v != '': skip = True
        if skip and verbose: print('skipping due to NULL constraint')
        return skip
    return False 

def null_filter(scene_struct, template, constraint, param_name_to_type, 
                state, outputs, verbose=False):
    p = constraint['params'][0]
    p_type = param_name_to_type[p]
    v = state['vals'].get(p)
    return is_null(v, p_type, verbose=verbose)
    
def out_neq_filter(scene_struct, template, constraint, param_name_to_type, 
                   state, outputs, verbose=False):
    i, j = constraint['params']
    i = state['input_map'].get(i, None)
    j = state['input_map'].get(j, None)
    if i is not None and j is not None and outputs[i] == outputs[j]:
        if verbose:
            print('skipping due to OUT_NEQ constraint')
            print(outputs[i])
            print(outputs[j])
        return True
    return False 

# constraint to avoid asking for object properties that was already mentioned in the dialogue history 
def unique_ques_obj_filter(scene_struct, template, constraint, all_constraints, param_name_to_type, 
                           state, outputs, verbose=False):
    vals = []
    for param in constraint['params']:
        param = state['input_map'].get(param, None)
        if param is not None:
            val = outputs[param]
            vals.append(val) 
        else:
            return False
    for val in vals:
        if val not in template['used_objects']: continue
        # avoid simulate the same unique object used previousely in template that cannot contain a reference
        if template['ref_remark'] == 'no_reference':
            return True
        used_obj = template['used_objects'][val]
        for c in all_constraints:
            if c['type'] == 'NULL':
                p = c['params'][0]
                p_type = param_name_to_type[p]
                strip_p = strip_attr_key(p)
                v = used_obj.get(strip_p, None)
                skip=is_null(v, p_type, verbose)
                if skip: 
                    return True 
            elif c['type'] in ['NOT_NULL_ACT', 'NOT_STATIC_ACT', 'STATIC_ACT', 'CONTAIN_ACT', 
                               'MINIMAL_ATTR', 'NONUNIQUE_ATTR', 'NONUNIQUE_ACT_ATTR',
                               'OUT_NEQ', 'UNIQUE_NEQ', 'NOT_CONTAIN_ACT']:
                pass
            else:
                print(c['type'])
                pdb.set_trace()
    return False 

# Avoid asking count/exist question when the resulting objects are just found objects in previous dialogue history 
def unique_ans_obj_filter(scene_struct, template, state, outputs, verbose=False):
    idx, ans_node = template['answer_obj']
    # since all interval are unique, skip check 
    if template['interval_type'] != 'none': return False
    # only check when the result objs are already obtained 
    if state['next_template_node'] != idx+1: return False
    result_objs = state['nodes'][-2]['_output']
    used_objs = template['used_objects']
    for o in result_objs:
        # Result objects contain a new object not found previously
        if o not in used_objs:
            return False
    return True



def exc_containing_filter(scene_struct, template, constraint, param_name_to_type, 
                          state, outputs, verbose=False):
    ps = constraint['params']
    skip = False
    for p in ps:
        v = state['vals'].get(p)
        if v is not None and v == 'containing':
            skip = True
            break
    if skip:
        if verbose:
            print("skipping due to EXC_CONTAINING constraint")
            print(constraint)
            print(state['vals'])
        return True
    return False 

'''
def not_gold_filter(scene_struct, template, constraint, param_name_to_type, state, outputs, verbose=False): 
    ps = constraint['params']
    skip = False
    for p in ps:
        v = state['vals'].get(p)
        if v is not None and v == 'gold':
            skip = True
            break
    if skip:
        if verbose:
            print('skipping due to NOT_GOLD constraint')
            print(constraint)
            print(state['vals'])
        return True 
    return False 

def not_snitch_filter(scene_struct, template, constraint, param_name_to_type, state, outputs, verbose=False):
    ps = constraint['params']
    skip = False
    for p in ps:
        v = state['vals'].get(p)
        if v is not None and v == 'spl':
            skip = True
            break
    if skip:
        if verbose:
            print('skipping due to NOT_SNITCH constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 

def out_neq_snitch_filter(scene_struct, template, constraint, param_name_to_type, state, outputs, verbose=False):
    i, j = constraint['params']
    i = state['input_map'].get(i, None)
    j = state['input_map'].get(j, None)
    sid = get_snitch_idx(scene_struct)
    if i is not None and j is not None and outputs[i] == outputs[j] and outputs[i] == [sid]:
        if verbose:
            print('skipping due to OUT_NEQ_SNITCH constraint')
            print(outputs[i])
            print(outputs[j])
            print(sid)
        return True
    return False 

def contain_shape_size_filter(scene_struct, template, constraint, param_name_to_type, 
                              state, outputs, verbose=False):
    ps = constraint['params']
    skip = False
    for p in ps:
        z1, s1, r, z2, s2 = p
        z1, s1, r, z2, s2 = state['vals'].get(z1), state['vals'].get(s1), state['vals'].get(r), \
            state['vals'].get(z2), state['vals'].get(s2)
        if r == 'containing':
            #print(z1, s1, r, z2, s2)
            if (s1 is not None and s1!= 'cone') \
                or (z1 is not None and z1=='small') \
                or (z2 is not None and z2=='large') \
                or not is_smaller(z2, z1):
                skip = True
                break
        elif r == 'contained':
            #print(z1, s1, r, z2, s2)
            if (s2 is not None and s2!= 'cone') \
                or (z2 is not None and z2=='small')  \
                or (z1 is not None and z1=='large') \
                or not is_smaller(z1, z2):
                skip = True
                break
    if skip:
        if verbose:
            print('skipping due to CONTAIN_SHAPE_SIZE constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 
'''


def contain_action_filter(scene_struct, template, constraint, param_name_to_type, 
                          state, outputs, verbose=False):
    ps = constraint['params']
    skip = False
    a1, r = ps
    a1, r = state['vals'].get(a1), state['vals'].get(r)
    if r == 'containing':
        print(a1, r)
        #pdb.set_trace()
        # limit action to sliding or stationary ot non-specific of container object 
        if a1 is not None and a1 not in ['sliding', 'static','']:
            skip = True
    elif r == 'contained':
        print(a1, r) 
        #pdb.set_trace()
        # contained object so its action should not be seen 
        if a1 is not None or a1!='':
            skip = True
    if skip:
        if verbose:
            print('skipping due to CONTAIN_ACT constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 

def not_contain_action_filter(scene_struct, template, constraint, param_name_to_type, 
                          state, outputs, verbose=False):
    ps = constraint['params']
    skip = False
    for p in ps:
        a = state['vals'].get(p)
        if a == 'contained':
            skip = True
            break
    if skip:
        if verbose:
            print('skipping due to NOT_CONTAIN_ACT constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 

# pass constraint if one of the action (not all actions) is not null
def not_null_action_filter(scene_struct, template, constraint, param_name_to_type, 
                           state, outputs, verbose=False):
    ps = constraint['params']
    vs = []
    for p in ps: 
        if p not in state['vals']: 
            return False 
        else:
            vs.append(state['vals'][p])
    skip = True
    for v in vs: 
        if v is not None and v!= '': 
            skip = False 
            break 
    if skip: 
        if verbose:
            print('skipping due to NOT_NULL_ACT constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 

# all actions must not be static 
def not_static_action_filter(scene_struct, template, constraint, param_name_to_type, 
                             state, outputs, verbose=False):
    ps = constraint['params']
    skip = False 
    for p in ps:
        v = state['vals'].get(p, None)
        if v is not None and v=='static': 
            skip = True 
            break 
    if skip: 
        if verbose:
            print('skipping due to NOT_STATIONARY_ACT constraint')
            print(constraint)
            print(state['vals'])
        return True
    return False 

def minimal_attribute_filter(scene_struct, template, constraint, param_name_to_type, 
                             state, outputs, verbose=False):
    identifiers = scene_struct['_minimal_object_identifiers']
    for node_idx, params in constraint['params']:
        i = state['input_map'].get(node_idx, None)
        if i is not None:
            #prior_i = state['input_map'][node_idx-1]
            #old_nodes = state['nodes'][prior_i+1:i]
            output = outputs[i]
            # if object are referred objects, exclude from this constraint 
            if output == template['prior_unique_obj']:
                continue
            if output == template['earlier_unique_obj']:
                continue
            identifier = get_identifier(params, state, param_name_to_type)
            # In case of 2 identical objects in video, skip
            if identifiers[output] is None:
                return True 
            if identifier in scene_struct['_minimal_object_identifiers'][output]:
                continue 
            identifier = random.sample(identifiers[output],1)[0]
            update_state(outputs, node_idx, params, param_name_to_type, identifier, state, scene_struct, template)
    return False 

def nonunique_attribute_filter(scene_struct, template, constraint, param_name_to_type, 
                               state, outputs, verbose=False):
    identifiers = scene_struct['_object_identifiers']
    for i, params in constraint['params']:
        i = state['input_map'].get(i, None)
        if i is not None:
            output = outputs[i]
            # if object are referred objects, exclude from this constraint 
            if output == template['prior_unique_obj']:
                continue
            if output == template['earlier_unique_obj']:
                #pdb.set_trace()
                # TODO
                continue
            curr_identifier = get_identifier(params, state, param_name_to_type)
            # In case of 2 identical objects in video
            if identifiers[output] is None:
                continue
            # if current identifier can identify unique object, skip
            if curr_identifier in identifiers[output]: 
                return True 
    return False  
