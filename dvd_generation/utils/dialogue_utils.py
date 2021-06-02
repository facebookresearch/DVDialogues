"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import argparse, json, os, itertools, random, shutil, copy
import time
import re
import pdb
import glob
from tqdm import tqdm
from utils.scene_utils import *
from filters.scene_filters import sample_cutoff
from utils.global_vars import *
from utils.utils import sample_by_prop

def strip_attr_key(key):
    if key in ['<Z>', '<C>', '<M>', '<S>', '<A>', '<R>']:
        return key 
    # e.g. <A2>, <Z4>, etc. 
    if len(key)!=4:
        pdb.set_trace()
    key = key[:2] + key[3]
    return key

def update_unique_object(obj_id, obj_attr, used_objects, turn_pos):
    if obj_id not in used_objects: 
        used_objects[obj_id] = {}
        used_objects[obj_id]['original_turn'] = turn_pos 
    if type(obj_attr)==list: pdb.set_trace()
    if obj_attr is None: pdb.set_trace()
    for k,v in obj_attr.items(): 
        if v is None:
            pdb.set_trace()
        if v in ['','thing']:
            pdb.set_trace()
        used_objects[obj_id][k] = v 
    
def find_unique_obj(turn, state, unique_obj, used_objects=None):
    # find value by backward the processing program
    unique_node_idx = state['input_map'][unique_obj[0]+1]-1
    
    obj_id = -1 
    for i in range(unique_node_idx,-1, -1):
        unique_node = state['nodes'][i]
        if unique_node['type'] in ['unique', 'unique_obj_ref', 'earlier_obj_ref']: 
            obj_id = unique_node['_output'] #, obj_attr
            break
    if obj_id==-1: pdb.set_trace()
        
    if used_objects is not None: 
        return obj_id, used_objects[obj_id]
    
    obj_attr = {}
    for a in unique_obj[1]['side_inputs']:
        strip_a = strip_attr_key(a)
        #print(state['vals'][a])
        if a not in state['vals']: continue 
        if '<A' in a: 
            # save period idx since value change by period 
            obj_attr[strip_a] = {'val': state['vals'][a], 
                           'period': turn['template']['used_periods'][-1]} 
                           #'interval_type': turn['template']['interval_type']}
        elif state['vals'][a] is not None and state['vals'][a] not in ['','thing']:
            obj_attr[strip_a] = state['vals'][a] 
            
    # Adding values from answer 
    # in case there are > 1 unique objects in question
    if len(unique_obj)==3:
        is_ans_obj = unique_obj[2]=='ans'
    else:
        is_ans_obj = True
    last_node = state['nodes'][-1]
    if is_ans_obj:
        if last_node['type'] in node_type_to_attribute.keys():
            obj_attr[node_type_to_attribute[last_node['type']]] =  last_node['_output']
    return obj_id, obj_attr 

def find_unique_answer_obj(turn, state, ans_obj, used_objects=None):
    obj_ids = turn['program'][-2]['_output']
    last_turn_que_type = turn['template']['nodes'][-1]['type']
    #if last_turn_que_type in ['count', 'exist']:
    #    return -1, None, obj_ids
    assert 'filter_exist' in last_turn_que_type \
        or 'filter_count' in last_turn_que_type \
        or last_turn_que_type in ['count', 'exist']
    # check that the previous answer results in 1
    if len(obj_ids)!=1:
        return -1, None, obj_ids
    obj_id = obj_ids[0]
    if used_objects is not None: 
        return obj_id, used_objects[obj_id], obj_ids
    obj_attr = {}
    if 'side_inputs' not in ans_obj[1]: 
        assert last_turn_que_type in ['count', 'exist']
        return obj_id, obj_attr, obj_ids
    for a in ans_obj[1]['side_inputs']:
        if a not in state['vals']: pdb.set_trace() 
        if '<A' in a: 
            obj_attr[a] = {'val': state['vals'][a], 
                           'period': turn['template']['used_periods'][-1], 
                           'interval_type': turn['template']['interval_type']}
        elif state['vals'][a] is not None and state['vals'][a] not in ['','thing']:
            obj_attr[a] = state['vals'][a] 
    return obj_id, obj_attr, obj_ids

def sample_unique_answer_obj(turn, state, ans_obj, used_objects, scene_struct):
    obj_ids = turn['program'][-2]['_output']
    last_turn_que_type = turn['template']['nodes'][-1]['type']
    if last_turn_que_type in ['exist'] or 'filter_exist' in last_turn_que_type:
        return obj_ids, -1, None, None
    assert 'filter_count' in last_turn_que_type \
        or last_turn_que_type in ['count']
    assert len(obj_ids)!=1
    if len(obj_ids)==0:
        return obj_ids, -1, None, None
    if set(obj_ids).issubset(set(used_objects.keys())):
        return obj_ids, -1, None, None
    unfound_objs = list(set(obj_ids) - set(used_objects.keys()))
    random.shuffle(unfound_objs)
    
    got_sample = False 
    for sampled_obj in unfound_objs:
        #sampled_obj = random.choice(list(unfound_objs))
        if len(obj_ids) == len(scene_struct['objects']):
            identifiers = scene_struct['_minimal_object_identifiers'][sampled_obj]
            if identifiers is None: continue 
            sampled_obj_attr = random.choice(identifiers)
            got_sample = True 
            break 
        else:
            objs = {}
            for oi in obj_ids:
                obj = {}
                for ai, a in enumerate(identifier_attrs):
                    obj[a] = scene_struct['objects'][oi][identifier_attr_names[ai]]
                objs[oi] = obj
            attr_maps = precompute_object_filter_options(objs)
            _, all_identifiers = precompute_obj_identifiers(attr_maps, objs)
            identifiers = all_identifiers[sampled_obj]
            if identifiers == [None]: continue 
            sampled_obj_attr = random.choice(identifiers)
            got_sample = True
            break
        
    if not got_sample:
    #    pdb.set_trace()
        return obj_ids, -1, None, None
        
    obj_attr = {}
    for idx, a in enumerate(identifier_attrs):
        if sampled_obj_attr[idx] is not None:
            obj_attr[a] = sampled_obj_attr[idx]
    sampled_obj_attr = copy.deepcopy(obj_attr)
    if 'side_inputs' not in ans_obj[1]: 
        assert last_turn_que_type in ['count']
        return obj_ids, sampled_obj, obj_attr, sampled_obj_attr
    for a in ans_obj[1]['side_inputs']:
        if a not in state['vals']: pdb.set_trace() 
        if '<A' in a: 
            obj_attr[a] = {'val': state['vals'][a], 
                           'period': turn['template']['used_periods'][-1], 
                           'interval_type': turn['template']['interval_type']}
        elif state['vals'][a] is not None and state['vals'][a] not in ['','thing']:
            obj_attr[a] = state['vals'][a] 
    return obj_ids, sampled_obj, obj_attr, sampled_obj_attr


def sample_identifier(scene_struct, obj_id):
    if obj_id is None:
        return None 
    identifiers = scene_struct['_minimal_object_identifiers'][obj_id]
    if identifiers is None: 
        return None 
    sample_identifier = random.sample(identifiers,1)[0]        
    obj_attrs = {}
    for idx, i in enumerate(sample_identifier): 
        if i is not None:
            obj_attrs[identifier_attrs[idx]] = i 
    return obj_attrs 
            
def sample_temporal_object_attr(scene_struct, period, cutoff):
    
    obj_id = get_period_obj(period, cutoff)
    #if obj_id_1 is not None and obj_id_2 is not None:
    #    if obj_id_1 != obj_id_2:
    #        pdb.set_trace()
    obj_attrs = sample_identifier(scene_struct, obj_id)
    return obj_id, obj_attrs
    #if obj_id_1 is not None:
    #    return obj_id_1, obj_attrs
    #else:
    #    obj_attrs = sample_identifier(scene_struct, obj_id_2)
    #    return obj_id_2, obj_attrs
        
    #if obj_id_1 is not None and obj_attrs_1 is None or 
    #    \ (obj_id_2 is not None and obj_attrs_2 is None):
    #    return obj_id_1, obj_attrs_1, obj_id_2, obj_attrs_2
    
    #return obj_id_1, obj_attrs_1, obj_id_2, obj_attrs_2 

def sample_relative_period(curr_periods, used_periods, period, interval_type, dependency, cutoff, scene_struct):
    e1, e2 = period
    end_video = cutoff[-1] if cutoff is not None else 301
    
    '''
    elif dependency=='after_before' and e2 is not None:
        found_e = False 
        for trial in range(100):
            next_e = random.choice(random.choice(scene_struct['grouped_events']))
            if 'moving' in next_e[1] or 'contain' in next_e[1]: 
                continue
            if 'start' not in next_e[1]:
                continue 
            if cutoff is None or next_e[-1] < cutoff[-1]:
                found_e = True
                break 
        if not found_e:
            return -1, None 
        new_period = (e2, next_e) 
    '''
    if dependency=='before' and e1 is not None and e1[-1] > interval_threshold:
        new_period = (None, e1) 
    elif dependency=='after' and e2 is not None and end_video-e2[-1] > interval_threshold:
        new_period = (e2, cutoff)
    else:
        return -1, None
    if new_period in curr_periods:
        period_idx = curr_periods.index(new_period)
        if new_period in used_periods:
            return -1, None
        else:
            return period_idx, new_period
    else:
        if interval_type != 'atomic': 
            pass
            #pdb.set_trace()
            #print("Unfound period: {}".format(new_period))
        return -1, None
    
# new type of temporal dependency derived from prior answer 
# e.g. how many sliding actions the red cube perform
def sample_among_prior_actions(dialogue, scene_struct, prior_period, cutoff): 
    tag = ''
    if dialogue[-1]['program'][-1]['type']=='action_count' and dialogue[-1]['answer']>1:
        obj_idx = dialogue[-1]['program'][dialogue[-1]['program'][-1]['inputs'][0]]['_output']
        action = dialogue[-1]['program'][-1]['side_inputs'][0]
        if len(scene_struct['objects'])-1 < obj_idx: pdb.set_trace()
        movements = scene_struct['movements'][scene_struct['objects'][obj_idx]['instance']]
        count = 0 
        all_counts = {}
        action_order = random.choice(range(1,dialogue[-1]['answer']+1))
        for movement in movements:
            a, _, s, e = movement
            if a == '_no_op': continue 
            mapped_a = action_map[a]
            if mapped_a not in all_counts: all_counts[mapped_a] = 0
            all_counts[mapped_a] += 1 
            prior_s = prior_period[0][-1] if prior_period[0] is not None else 0
            prior_e = prior_period[1][-1] if prior_period[1] is not None else len(scene_struct['objects'][0]['locations'])-1
            if is_overlap(s,e, prior_s, prior_e, return_overlap=True)>overlap_threshold \
                and (mapped_a == action or action == 'moving'):
                count += 1 
            if count == action_order:
                e1 = (obj_idx, 'start_'+ mapped_a, all_counts[mapped_a], movement[2])
                e2 = (obj_idx, 'end_'+ mapped_a, all_counts[mapped_a], movement[3])
                if e - s > interval_threshold:
                    if cutoff is None or (cutoff is not None and e2[-1]<=cutoff[-1]): 
                        prior_period = (e1,e2) 
                        tag = '{}_{}_among_'.format(action_order, action)
                break    
    return tag, prior_period 

def sample_unique_answer_action(dialogue, scene_struct, prior_period, cutoff): 
    tag = ''
    if dialogue[-1]['program'][-1]['type']=='query_action_order' and dialogue[-1]['answer']!='no action':
        obj_idx = dialogue[-1]['program'][dialogue[-1]['program'][-1]['inputs'][0]]['_output']
        movements = scene_struct['movements'][scene_struct['objects'][obj_idx]['instance']]
        action = dialogue[-1]['answer']
        action_order = dialogue[-1]['program'][-1]['side_inputs'][0] 
        if action_order != 'last':
            action_order = reverse_ordinal_map[action_order]
        count = 0 
        all_counts = {}
        found = False 
        for movement in movements:
            a, _, s, e = movement
            if a == '_no_op': continue 
            mapped_a = action_map[a]
            if mapped_a not in all_counts: all_counts[mapped_a] = 0
            all_counts[mapped_a] += 1 
            
            prior_s = prior_period[0][-1] if prior_period[0] is not None else 0
            prior_e = prior_period[1][-1] if prior_period[1] is not None else len(scene_struct['objects'][0]['locations'])-1
            if is_overlap(s,e, prior_s, prior_e, return_overlap=True)>overlap_threshold:
                count += 1 
                e1 = (obj_idx, 'start_'+ mapped_a, all_counts[mapped_a], movement[2])
                e2 = (obj_idx, 'end_'+ mapped_a, all_counts[mapped_a], movement[3])
                found = True 
                
            if action_order!='last' and count == action_order:
                if cutoff is None or (cutoff is not None and e2[-1]<=cutoff[-1]): 
                    prior_period = (e1, e2) 
                    tag = 'prior_{}_'.format(action)
                break        
                
        if action_order == 'last':
            if not found: pdb.set_trace()
            if cutoff is None or (cutoff is not None and e2[-1]<=cutoff[-1]): 
                prior_period = (e1, e2) 
                tag = 'prior_{}_'.format(action)
    return tag, prior_period
    
def precompute_object_filter_options(objects):
    # Keys are tuples (size, color, shape, material) (where some may be None)
    # and values are lists of object idxs that match the filter criterion
    attribute_map = {}
    #attr_keys = ['<Z>', '<C>', '<M>', '<S>']
    # Precompute masks
    masks = []
    for i in range(2**len(identifier_attrs)):
        mask = []
        for j in range(len(identifier_attrs)):
            mask.append((i // (2**j)) % 2)
        masks.append(mask)

    for object_idx, obj in objects.items():
        key = []
        for k in identifier_attrs:
            if k in obj: 
                key.append(obj[k])
            else:
                key.append(None) 
        keys = [tuple(key)]
        #keys = [tuple([obj[k] for k in attr_keys if k in obj else 'unknown'])]
        for mask in masks:
            for key in keys:
                masked_key = []
                for a, b in zip(key, mask):
                    if b == 1:
                        masked_key.append(a)
                    else:
                        masked_key.append(None)
                masked_key = tuple(masked_key)
                if masked_key not in attribute_map:
                    attribute_map[masked_key] = set()
                attribute_map[masked_key].add(object_idx)
    return attribute_map

def precompute_obj_identifiers(attribute_map, objects):
    out = {}
    #duplicate_objs = False 
    for k,v in attribute_map.items(): 
        if len(v) != 1: continue 
        obj = list(v)[0]
        if obj not in out: out[obj] = []
        out[obj].append(k)
    #if len(out) != len(scene_struct['objects']): duplicate_objs = True  
    output = {i:[None] for i in objects.keys()}
    num_not_nones = {i:[None] for i in  objects.keys()}
    for k,v in out.items():
        output[k] = v 
        num_not_none = []
        for i in v: 
            num_not_none.append(int(i[0]!=None)+int(i[1]!=None)+int(i[2]!=None)+int(i[3]!=None))
        num_not_nones[k] = num_not_none
    for k,v in output.items():
        if (None,None,None,None) in v: 
            idx = v.index((None,None,None,None))
            output[k].pop(idx) 
            num_not_nones[k].pop(idx)
    minimal_output = {i:[None] for i in output.keys()} 
    for i, os in output.items(): 
        if os == None: continue 
        if len(os) == 0: continue 
        #if len(num_not_nones[i])==0:
        #    pdb.set_trace()
        m = min(num_not_nones[i]) #avoid (None,None,None,None)
        if m==0: pdb.set_trace()
        identifiers = []
        for j, o in enumerate(os): 
            if num_not_nones[i][j] == m: 
                identifiers.append(o)
        minimal_output[i] = identifiers
    return output, minimal_output

def sample_period_idx(dialogue, template, scene_struct, used_periods, turn_dependencies, last_unique_obj_idx):
    last_unique_obj = False
    earlier_unique_obj = False
    cutoff = template['cutoff']
    whole_video_period = (None, cutoff)
    
    if template['interval_type'] != 'none': 
        curr_periods = scene_struct[intervals_to_periods[template['interval_type']]] 
        trial = 0 
        
        while(True):
            trial += 1 
            if whole_video_period not in curr_periods and template['interval_type']=='compositional': pdb.set_trace()
            # to avoid explosion of memory when sampling the next interval 
            if trial==max_period_sampling_attempts: 
                return -1 
            # encouring period as a whole video, limit to one repetition over contiguous turns 
            if sample_by_prop(whole_video_p) and whole_video_period in curr_periods:
                if len(used_periods)==0 \
                or (len(used_periods)>0 and used_periods[-1] != whole_video_period): 
                    new_period = whole_video_period 
                    used_periods.append(new_period)
                    period_idx = curr_periods.index(new_period)
                    break
            # sample the remaining except for whole video period
            period_idx = random.choice(range(len(curr_periods)))
            new_period = curr_periods[period_idx]            
            if not is_valid_event(new_period, cutoff): 
                continue            
            # sampled cases are new unseen period only
            if sample_by_prop(unique_interval_p) and new_period in used_periods: continue 
                
            # if there is last unique object, encouraging temporal dependency with reference to the last unique object 
            if sample_by_prop(last_unique_period_p) and len(dialogue)>0 and last_unique_obj_idx!=-1: 
                # check if can refer to the interval of the same object mentioned previously 
                if not is_obj_of_period(last_unique_obj_idx, curr_periods[period_idx]): continue 
                last_unique_obj = True 
                template['temporal_obj_id'], template['temporal_obj_attr'] = \
                    last_unique_obj_idx, template['prior_unique_obj_attr']
                #template['temporal_obj_id_2'], template['temporal_obj_attr_2'] = \
                #    last_unique_obj_idx, template['prior_unique_obj_attr']
                    
            # if there is earlier unique object, encouraging temporal dependency with reference to the earlier mentioned object 
            elif sample_by_prop(earlier_unique_period_p) and len(dialogue)>0 and len(template['used_objects'])>0:
                dial_obj_identifiers = template['_dial_minimal_object_identifiers']
                temp = copy.deepcopy(list(template['used_objects'].keys()))
                random.shuffle(temp)
                found_earlier = False 
                for earlier_unique_obj_idx in temp:
                    if dial_obj_identifiers[earlier_unique_obj_idx] != [None]:
                        found_earlier = True 
                        break 
                if not found_earlier: continue
                # check if can refer to the interval of the same object mentioned previously 
                if not is_obj_of_period(earlier_unique_obj_idx, curr_periods[period_idx]): continue 
                earlier_unique_obj_attr = random.choice(dial_obj_identifiers[earlier_unique_obj_idx])
                if earlier_unique_obj_attr is None: pdb.set_trace()
                earlier_unique_obj_attr = {identifier_attrs[k]:v for k,v in enumerate(earlier_unique_obj_attr) \
                                           if v is not None}
                earlier_unique_obj = True 
                template['temporal_obj_id'], template['temporal_obj_attr'] = \
                    earlier_unique_obj_idx, earlier_unique_obj_attr
                #template['temporal_obj_id_2'], template['temporal_obj_attr_2'] = \
                #    earlier_unique_obj_idx, earlier_unique_obj_attr

            else:
                oi, oa = sample_temporal_object_attr(scene_struct, curr_periods[period_idx], cutoff)
                #if (oi1 is not None and oa1 is None) or (oi2 is not None and oa2 is None): continue 
                if oi is not None and oa is None: continue 
                template['temporal_obj_id'], template['temporal_obj_attr'] = oi, oa
                #template['temporal_obj_id_2'], template['temporal_obj_attr_2'] = oi2, oa2 
            used_periods.append(new_period)
            break
    else:
        used_periods.append(None)
        period_idx = -1
        
    if last_unique_obj: 
        turn_dependencies['temporal'] = 'last_unique_obj_none'
    elif earlier_unique_obj:
        turn_dependencies['temporal'] = 'earlier_unique_obj_none'
    else:
        turn_dependencies['temporal'] = 'none'

    return period_idx 
