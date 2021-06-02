"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json, os, math
import pdb
from collections import defaultdict
from collections import Counter 
from utils.utils import *
from utils.global_vars import *
from utils.scene_utils import remove_contained_act, convert_to_compositional_period_idx

'''
def action_filter_handler(scene_struct, inputs, side_inputs, period_idx, period_relation=None):
    assert len(inputs) == 1
    assert len(side_inputs) == 1
    value = side_inputs[0]
    output = []
    for idx in inputs[0]:
        all_moves = get_action_by_moment(scene_struct, idx, period_idx, include_moving=True)
        if value in all_moves: 
            output.append(idx) 
    return output
'''

def actions_filter_handler(scene_struct, inputs, side_inputs, period_idx, 
                           period_relation='during', interval_type='compositional'):
    assert len(inputs) == 1
    assert len(side_inputs) == 1
    value = side_inputs[0]
    output = []
    if interval_type == 'atomic':
        period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
    for idx in inputs[0]:
        all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
        no_contained_moves = remove_contained_act(all_moves)
        if value=='static':
            if all_moves is None or no_contained_moves is None: 
                output.append(idx)
            continue 
        #assert len(all_moves)>0
        #no_contain_moves = [a for a in all_moves if a!='contained'] 
        #all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
        #all_moves = remove_contained_act(all_moves)
        if value=='moving' and no_contained_moves is not None:  #and len(no_contain_moves)>0: #and value in no_contain_moves:
            output.append(idx)
            continue 
        if all_moves is not None and value in all_moves: 
            output.append(idx)
            continue 
    return output

def relate_handler(scene_struct, inputs, side_inputs, period_idx, period_relation=None):
    assert len(inputs) == 1
    assert len(side_inputs) == 1
    relation = side_inputs[0]
    return scene_struct['relationships'][period_idx][relation][inputs[0]]

def action_count_handler(scene_struct, inputs, side_inputs, period_idx, period_relation='during'):
    assert len(inputs) == 1
    assert len(side_inputs) == 1 
    #assert side_inputs[0] != 'contained' 
    #assert side_inputs[0] != 'static' 
    idx = inputs[0]
    actions = scene_struct['_action_list'][period_idx][period_relation][idx]
    count = 0
    if actions is not None:
        if side_inputs[0] == 'moving':
            count = len([a for a in actions if a!='contained'])
        else:
            for a in actions:
                if side_inputs[0] == a:
                    count += 1
    return count 

'''
def same_action_handler(scene_struct, inputs, side_inputs, period_idx, period_relation=None):
    pdb.set_trace()
    cache_key = '_same_action_period_{}'.format(period_idx)
    if cache_key not in scene_struct:
        cache = {}
        for i, obj1 in enumerate(scene_struct['objects']):
            same = []
            a1 = get_action_by_moment(scene_struct, i, period_idx, include_moving=False)
            assert len(a1)==1
            a1 = list(a1)[0]
            for j, obj2 in enumerate(scene_struct['objects']):
                if i != j:
                    a2 = get_action_by_moment(scene_struct, j, period_idx, include_moving=False)
                    assert len(a2)==1
                    a2 = list(a2)[0]
                    if a1 == a2: 
                        same.append(j) 
            cache[i] = same
        scene_struct[cache_key] = cache
    cache = scene_struct[cache_key]
    assert len(inputs) == 1
    assert len(side_inputs) == 0
    return cache[inputs[0]]
'''

def make_same_actions_handler(seq_type):
    def same_actions_handler(scene_struct, inputs, side_inputs, period_idx, period_relation='during'):
        actions = scene_struct['_action_list'][period_idx][period_relation]
        objects = scene_struct['objects']
        cache_key = '_same_action_{}_period_{}'.format(seq_type, period_idx)
        if cache_key not in scene_struct:
            cache = {}
            for i, obj1 in enumerate(objects):
                a1 = remove_contained_act(actions[i])
                if seq_type == 'set': 
                    a1 = sorted(set(a1)) if a1 is not None else a1
                same = []
                for j, obj2 in enumerate(objects):
                    if i != j:
                        a2 = remove_contained_act(actions[j])
                        if seq_type == 'set': 
                            a2 = sorted(set(a2)) if a2 is not None else a2
                        if a1 == a2: 
                            same.append(j) 
                cache[i] = same
            scene_struct[cache_key] = cache
        cache = scene_struct[cache_key]
        assert len(inputs) == 1
        assert len(side_inputs) == 0
        return cache[inputs[0]]
    return same_actions_handler

def make_query_action_handler(attribute):
    def query_action_handler(scene_struct, inputs, side_inputs, period_idx, period_relation='during'):
        assert len(inputs) == 1
        if len(side_inputs) != 0 and attribute not in ['action_order', 'action_freq']:
            pdb.set_trace()
        idx = inputs[0]
        obj = scene_struct['objects'][idx]
        if attribute == 'action': 
            period_idx = period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
            all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
            all_moves = remove_contained_act(all_moves)
            if all_moves is not None: 
                assert len(all_moves)==1
                return next(iter(all_moves))
            return 'no action'
            #all_moves = get_action_by_moment(scene_struct, idx, period_idx, include_moving=False)
            #assert len(all_moves)==1
            #if  list(all_moves)[0] == 'static' or  list(all_moves)[0] == 'stationary':
            #    return 'no action'
            #return list(all_moves)[0]
        elif attribute == 'action_set':
            all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
            all_moves = remove_contained_act(all_moves)
            if all_moves is not None: 
                return ','.join(sorted(set(all_moves)))
            return 'no action'
        elif attribute == 'action_seq':
            all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
            all_moves = remove_contained_act(all_moves)
            if all_moves is not None: 
                return ','.join(all_moves)
            return 'no action'
        elif attribute == 'action_order':
            all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
            all_moves = remove_contained_act(all_moves)
            if all_moves is not None: 
                assert len(all_moves)>0
                if side_inputs[0] == 'last':
                    return all_moves[-1]
                else:
                    order = reverse_ordinal_map[side_inputs[0]]
                    if len(all_moves)>=order:
                        return all_moves[order-1]
            return 'no action'
        elif attribute == 'action_freq':
            all_moves = scene_struct['_action_list'][period_idx][period_relation][idx]
            all_moves = remove_contained_act(all_moves)
            out = []
            if all_moves is not None: 
                assert len(all_moves)>0
                all_freqs = Counter(all_moves)
                if side_inputs[0] == 'the most': 
                    freq = max(all_freqs.values())
                elif side_inputs[0] == 'the least':
                    freq = min(all_freqs.values())
                else:
                    freq = frequency_to_number[side_inputs[0]]
                for k,v in all_freqs.items():
                    if v == freq:
                        out.append(k)
            if len(out)>0:
                return ','.join(sorted(set(out)))
            return 'no action'
        else:
            pdb.set_trace()

    return query_action_handler
