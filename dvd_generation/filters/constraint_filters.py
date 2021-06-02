"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

from filters.spatial_constraint_filters import *
from filters.temporal_constraint_filters import *

spatial_constraint_filter_map = {
    'NULL': null_filter,
    'OUT_NEQ': out_neq_filter, 
    'EXC_CONTAINING': exc_containing_filter, 
    #'NOT_GOLD': not_gold_filter, 
    #'NOT_SNITCH': not_snitch_filter,
    #'OUT_NEQ_SNITCH': out_neq_snitch_filter,
    #'CONTAIN_SHAPE_SIZE': contain_shape_size_filter,
    'CONTAIN_ACT': contain_action_filter,
    'NOT_CONTAIN_ACT': not_contain_action_filter, 
    'NOT_NULL_ACT': not_null_action_filter,
    'NOT_STATIC_ACT': not_static_action_filter,
    'MINIMAL_ATTR': minimal_attribute_filter,
    'NONUNIQUE_ATTR': nonunique_attribute_filter,
}

temporal_constraint_filter_map = {
    'UNIQUE_NEQ': unique_neq_filter, 
    'STATIC_ACT': static_action_filter,    
    'MINIMAL_ACT_ATTR': minimal_action_attribute_filter,
    'NONUNIQUE_ACT_ATTR': nonunique_action_attribute_filter,
}

def constraint_filters(scene_struct, template, param_name_to_type, state, outputs, period_idx, 
                       verbose=False, turn_dependencies=None): 
    skip_state = False 
    constraints = template['constraints']
    found_unique_ques_obj = False 
    found_unique_ans_obj = template['answer_obj'] is not None
    period_relation = 'excluding' if turn_dependencies['temporal'] == 'excluding' else 'during'
    for constraint in constraints:
        ct = constraint['type']
        #assert constraint['type'] in constraint_filter_map, 'Unrecognized constraint type "%s"' % constraint['type']
        if ct in spatial_constraint_filter_map:
            constraint_filter = spatial_constraint_filter_map[ct]
            skip_state = constraint_filter(scene_struct, template, constraint, param_name_to_type, 
                                           state, outputs, verbose=False)
        elif ct in temporal_constraint_filter_map:
            constraint_filter = temporal_constraint_filter_map[ct]
            skip_state = constraint_filter(scene_struct, template, constraint, param_name_to_type, 
                                           state, outputs, period_idx, period_relation, verbose=False)
        else:
            pdb.set_trace()
        if skip_state: return skip_state 
        if constraint['type'] == 'UNIQUE_NEQ': 
            found_unique_ques_obj = True
            unique_constraint = constraint
    if found_unique_ques_obj:
        skip_state = unique_ques_obj_filter(scene_struct, template, unique_constraint, constraints, 
                                            param_name_to_type, state, outputs, verbose=False)
        if skip_state: return skip_state
    if found_unique_ans_obj:
        skip_state = unique_ans_obj_filter(scene_struct, template, state, outputs, verbose=False)
        if skip_state: return skip_state
    return skip_state
