"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import pdb
import copy
import random

action_map = {'_slide': 'sliding', '_rotate': 'rotating', '_pick_place': 'flying', 
                 '_contain': 'flying'}

def is_valid_event(period, events):
    e1, e2 = period
    if e1 is not None:
        if 'moving' in e1[1]: return False 
        if 'contain' in e1[1]: return False
    if e2 is not None:
        if 'moving' in e2[1]: return False 
        if 'contain' in e2[1]: return False
        
    if e1 is None and e2 is None: 
        return True    
    elif e1 is None:
        return True 
    elif e2 is None:
        return True
    else:
        if e1[0] == e2[0]:
            if e1[1].split('_')[0]=='start' and e2[1].split('_')[0]=='end':
                return True
            elif e1[1].split('_')[0]=='end' and e2[1].split('_')[0]=='start':
                return True
            else:
                return False 
        else:
            return False 

def find_all_periods(scene, threshold, cutoff_t=-1):
    scene_tag = '' if cutoff_t==-1 else '_till_{}'.format(cutoff_t) 
    movements = scene['movements']
    events = []
    
    has_contain = False 
    for o, ms in movements.items(): 
        order = {'sliding': 0, 'rotating': 0, 'flying':0, 'moving': 0}
        obj_id = scene['obj_id_to_idx'][o]
        prior_end = -1 
        for m in ms:
            if m[0]=='_no_op': continue 
            if 'contain' in m[0]: 
                has_contain = True 
            a = action_map[m[0]]
            s = m[2]
            e = m[3]
            if cutoff_t!=-1 and e>cutoff_t: continue 
                
            # specific movement 
            th = order[a]+1
            order[a] += 1 
            # all types of movement 
            all_th = order['moving']+1
            order['moving'] += 1 
            
            # check if each object cannot have more than one event at once 
            # check if all actions are already sorted in CATER 
            assert s >= prior_end 
            prior_end = e 
            events.append((obj_id, 'start_{}'.format(a), th, s))
            events.append((obj_id, 'end_{}'.format(a), th, e))
            events.append((obj_id, 'start_{}'.format('moving'), all_th, s))
            events.append((obj_id, 'end_{}'.format('moving'), all_th, e))
    scene['has_contain'] = has_contain
    
    # Adding containment as an temporal state like actions 
    contained_events = scene['contained_events']
    for obj_id, cs in contained_events.items():
        assert len(cs) == len(set(cs))
        sorted_cs = sorted(cs, key=lambda x: x[0])
        order = 0 
        for c in cs:
            s, e = c
            th = order+1
            order += 1 
            events.append((obj_id, 'start_{}'.format('contained'), th, s))
            events.append((obj_id, 'end_{}'.format('contained'), th, e))
    
      
    events = sorted(events, key=lambda x: x[-1])
    grouped_events = []
    event_to_group = {}
    curr_t = events[0][-1]
    curr_group = []
    for idx, event in enumerate(events): 
        if event[-1] != curr_t and idx>0: 
            grouped_events.append(curr_group) 
            curr_group = []
            curr_t = event[-1]
        curr_group.append(event)
        event_to_group[idx] = len(grouped_events)
    grouped_events.append(curr_group)
    scene['events{}'.format(scene_tag)] = events 
    scene['grouped_events{}'.format(scene_tag)] = grouped_events 
    scene['event_to_group'] = event_to_group
    
    event_periods = []
    if grouped_events[0][0][-1]>threshold:
        for e in grouped_events[0]: 
            event_periods.append((None, e))
    has_eov = False
    has_sov = False
    curr_start = grouped_events[0][0][-1]
    curr_events = grouped_events[0] 
    if curr_start == 0: 
        has_sov = True
    t_eov = len(scene['objects'][0]['locations'])-1 if cutoff_t==-1 else cutoff_t
    if grouped_events[-1][0][-1] == t_eov:
        has_eov = True 
    for es in grouped_events[1:]:
        t = es[0][-1]
        if t - curr_start > threshold: 
            for e1 in curr_events:
                for e2 in es:
                    event_periods.append((e1, e2))
        curr_start = t 
        curr_events = es 
    if has_eov:
        for e in grouped_events[-2]:
            event_periods.append((e, None)) # last frame of video
    else: 
        for e in grouped_events[-1]: 
            event_periods.append((e, None)) # last frame of video 
    if has_sov:
        for e in grouped_events[1]: 
            event_periods.append((None, e)) # first frame of video 
    else:
        for e in grouped_events[0]: 
            event_periods.append((None, e)) # first frame of video 
    # Trim event periods 
    out_periods = []
    for p in event_periods:
        if not is_valid_event(p, events): continue
        out_periods.append(p)
        
    if len(out_periods)==0:
        pdb.set_trace()

    scene['periods{}'.format(scene_tag)]=out_periods     

def find_all_compositional_periods(scene, threshold, cutoff_t=-1):
    scene_tag = '' if cutoff_t==-1 else '_till_{}'.format(cutoff_t) 
    grouped_events = scene['grouped_events{}'.format(scene_tag)]
    event_periods = set()
    t_eov = len(scene['objects'][0]['locations'])- 1 if cutoff_t==-1 else cutoff_t
    for start_index in range(0,len(grouped_events)):
        curr_start = grouped_events[start_index][0][-1]
        curr_events = grouped_events[start_index]       
        if start_index < len(grouped_events)-1:  
            # compositional periods include non-compositional periods as well 
            for end_index in range(start_index+1, len(grouped_events)):  
                es = grouped_events[end_index]
                t = es[0][-1]
                if t - curr_start > threshold: 
                    for e1 in curr_events:
                        for e2 in es:
                            event_periods.add((e1, e2))
        if curr_start != t_eov:
            for e1 in curr_events:
                event_periods.add((e1, None))
        if curr_start != 0: 
            for e1 in curr_events:
                event_periods.add((None, e1)) 

    event_periods.add((None, None)) 
    # Trim event periods 
    out_periods = []
    for p in event_periods:
        if not is_valid_event(p, scene['events']): continue
        out_periods.append(p)
                
    if len(out_periods)==0:
        pdb.set_trace()
    scene['all_periods{}'.format(scene_tag)]=out_periods
    
def find_obj_location_by_moment(scene_struct, obj, moment, s1, e1): 
    actions = scene_struct['movements'][obj['instance']]
    for action in actions: 
        if action in ['_no_op', '_rotate']: continue 
        s2 = action[2]
        e2 = action[3]
        if is_overlap(s1, e1, s2, e2): 
            return obj['locations'][str(s1)], obj['locations'][str(e1)]
    return obj['locations'][str(moment)], None 

def is_overlap(s1, e1, s2, e2, return_overlap=False):
    if return_overlap:
        if s2<e1 and s1<e2:
            return min(e1,e2)-max(s1,s2)
        else:
            return 0 
    return s2<e1 and s1<e2

def get_all_containment_periods(scene_struct): 
    contain_movements = []
    movements = scene_struct['movements']
    objects = scene_struct['objects']
    containment_periods = {} 
    for obj_id, ms in movements.items():
        obj = objects[scene_struct['obj_id_to_idx'][obj_id]]
        if obj['shape'] == 'cone': 
            for idx_m, m in enumerate(ms):
                if m[0] == '_contain': 
                    contain_movements.append((obj_id, idx_m))
    for m in contain_movements:
        movement = movements[m[0]][m[1]]
        start = movement[3]
        end = len(scene_struct['objects'][0]['locations'])-1
        if m[1] != len(movements[m[0]])-1:
            for m1 in movements[m[0]][m[1]+1:]:
                if m1[0] == '_pick_place':
                    end = m1[2]  # end of containment period 
                    break 
        if m[0] not in containment_periods: containment_periods[m[0]] = []
        containment_periods[m[0]].append([movement[1], start, end])
    
    contained_events = {} 
    for obj_idx in range(len(scene_struct['objects'])):
        contained_events[obj_idx] = [] 
    for cs in containment_periods.values():
        for c in cs: 
            containee, s, e = c 
            obj_idx = scene_struct['obj_id_to_idx'][containee] 
            contained_events[obj_idx].append((s,e))
    scene_struct['contained_events'] = contained_events


def compute_all_relationships(scene_struct, start, end, moment, idx, eps=0.2):
    """
    Computes relationships between all pairs of objects in the scene.

    Returns a dictionary mapping string relationship names to lists of lists of
    integers, where output[rel][i] gives a list of object indices that have the
    relationship rel with object i. For example if j is in output['left'][i]
    then object j is left of object i.
    """
    all_relationships = {}
    for name, direction_vec in scene_struct['directions'].items():
        if name == 'above' or name == 'below':
            continue
        all_relationships[name] = []
        for i, obj1 in enumerate(scene_struct['objects']):
            coords1_start, coords1_end = find_obj_location_by_moment(scene_struct, obj1, moment, start, end) 
            related = set()
            if coords1_end is None: #obj1 must be static only 
                for j, obj2 in enumerate(scene_struct['objects']):
                    if obj1 == obj2:
                        continue
                    coords2_start, coords2_end = find_obj_location_by_moment(scene_struct, obj2, moment, start, end) 
                    diff = [coords2_start[k] - coords1_start[k] for k in [0, 1, 2]]
                    dot = sum(diff[k] * direction_vec[k] for k in [0, 1, 2])
                    is_related = dot > eps 
                    if coords2_end is not None:
                        end_diff = [coords2_end[k] - coords1_start[k] for k in [0, 1, 2]]
                        end_dot = sum(end_diff[k] * direction_vec[k] for k in [0, 1, 2])
                        is_related = dot > eps and end_dot > eps 
                    if is_related: 
                        related.add(j)
            all_relationships[name].append(sorted(list(related)))
    scene_struct['relationships'][idx] = all_relationships

def remove_snitch_filter_options(attribute_map, with_action=False):
    out = {}
    # If it is snitch, keep only combinations that are minimal
    # remove redudant ones e.g. 'small gold metallic snitch', 'gold snitch'
    unique_options = [(None, 'gold', None, None), (None, None, None, 'spl')]
    for k, v in attribute_map.items():
        if 'gold' in k or 'spl' in k:
            if with_action:
                if k[1:] not in unique_options: continue 
            else:
                if k not in unique_options: continue
        out[k] = v
    return out

def precompute_filter_options(scene_struct):
    # Keys are tuples (size, color, shape, material) (where some may be None)
    # and values are lists of object idxs that match the filter criterion
    attribute_map = {}

    attr_keys = ['size', 'color', 'material', 'shape']

    # Precompute masks
    masks = []
    for i in range(2**len(attr_keys)):
        mask = []
        for j in range(len(attr_keys)):
            mask.append((i // (2**j)) % 2)
        masks.append(mask)

    for object_idx, obj in enumerate(scene_struct['objects']):
        keys = [tuple(obj[k] for k in attr_keys)]

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

    attribute_map = remove_snitch_filter_options(attribute_map)
    scene_struct['_filter_options'] = attribute_map
    
def precompute_obj_identifiers(scene_struct):
    out = {}
    duplicate_objs = False 
    for k,v in scene_struct['_filter_options'].items(): 
        if len(v) != 1: continue 
        obj = list(v)[0]
        if obj not in out: out[obj] = []
        out[obj].append(k)
    if len(out) != len(scene_struct['objects']): duplicate_objs = True  
    output = [None] * len(scene_struct['objects'])
    num_not_nones = [None] * len(scene_struct['objects'])
    for k,v in out.items():
        output[k] = v 
        num_not_none = []
        for i in v: 
            num_not_none.append(int(i[0]!=None)+int(i[1]!=None)+int(i[2]!=None)+int(i[3]!=None))
        num_not_nones[k] = num_not_none
    minimal_output = [None] * len(output) 
    for i, os in enumerate(output): 
        if os == None: continue 
        m = min(num_not_nones[i])
        identifiers = []
        for j, o in enumerate(os): 
            if num_not_nones[i][j] == m: 
                identifiers.append(o)
        minimal_output[i] = identifiers 
    scene_struct['_object_identifiers'] = output
    scene_struct['_minimal_object_identifiers'] = minimal_output 
    return duplicate_objs

def precompute_obj_identifiers_with_action(scene_struct, period_idx, interval_type, relation):
    if interval_type=='atomic':
        filter_options = scene_struct['_action_filter_options'][period_idx]
        all_identifiers = scene_struct['_object_identifiers_with_action']
        min_identifiers = scene_struct['_minimal_object_identifiers_with_action']
    elif interval_type == 'compositional':
        filter_options = scene_struct['_actions_filter_options'][period_idx][relation]
        all_identifiers = scene_struct['_object_identifiers_with_actions']
        min_identifiers = scene_struct['_minimal_object_identifiers_with_actions']
    out = {}
    duplicate_objs = False 
    for k,v in filter_options.items(): 
        #if k[0] is None: continue 
        if len(v) != 1: continue 
        obj = list(v)[0]
        if obj not in out: out[obj] = []
        out[obj].append(k)
    #pdb.set_trace()
    if len(out) != len(scene_struct['objects']): duplicate_objs = True  
    output = [None] * len(scene_struct['objects'])
    num_not_nones = [None] * len(scene_struct['objects'])
    for k,v in out.items():
        output[k] = v 
        num_not_none = []
        for i in v: 
            num_not_none.append(int(i[0]!=None)+int(i[1]!=None)+int(i[2]!=None)+int(i[3]!=None)+int(i[4]!=None))
        num_not_nones[k] = num_not_none
    minimal_output = [None] * len(output) 
    for i, os in enumerate(output): 
        if os == None: continue 
        m = min(num_not_nones[i])
        identifiers = []
        for j, o in enumerate(os): 
            if num_not_nones[i][j] == m: 
                identifiers.append(o)
        minimal_output[i] = identifiers 
    #only include identifiers with action as !None 
    action_minimal_output = [None] * len(output) 
    for k,vs in enumerate(minimal_output):
        act_vs = []
        if vs is None: continue 
        for v in vs:
            if v[0] is None: continue 
            act_vs.append(v)
        if len(act_vs)>0:
            action_minimal_output[k] = act_vs
    if interval_type=='atomic':
        all_identifiers[period_idx] = output 
        min_identifiers[period_idx] = action_minimal_output 
    elif interval_type == 'compositional':
        if period_idx not in all_identifiers:
            all_identifiers[period_idx] = {} 
            min_identifiers[period_idx] = {}
        all_identifiers[period_idx][relation] = output 
        min_identifiers[period_idx][relation] = action_minimal_output 
    return duplicate_objs

def remove_invalid_action_options(attribute_map):
    out = {} 
    for k,v in attribute_map.items():
        if 'sphere' in k and 'rotating' in k: continue 
        out[k] = v
    return out 

def precompute_actions_filter_options(scene_struct, period_idx):
    attr_keys = ['action', 'size', 'color', 'material', 'shape']
    # Precompute masks
    masks = []
    for i in range(2**len(attr_keys)):
        mask = []
        for j in range(len(attr_keys)):
            mask.append((i // (2**j)) % 2)
        masks.append(mask)
    
    scene_struct['_actions_filter_options'][period_idx] = {} 
    for relation in ['during', 'excluding']:
        attribute_map = {}
        for object_idx, obj in enumerate(scene_struct['objects']):
            keys = []
            contained = False 
            attr_key = [obj[k] for k in attr_keys[1:]]
            actions = scene_struct['_action_list'][period_idx][relation][object_idx]
            
            if actions is not None: 
                for a in actions:
                    keys.append(tuple([a] + attr_key))
                no_contained_actions = [a for a in actions if a!='contained']
                if 'contained' in actions: 
                    contained = True
                if len(no_contained_actions)>0:
                    keys.append(tuple(['moving'] + attr_key))
            else:
                keys.append(tuple([None] + attr_key))

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
        
        attribute_map = remove_snitch_filter_options(attribute_map, with_action=True)
        attribute_map = remove_invalid_action_options(attribute_map)
        scene_struct['_actions_filter_options'][period_idx][relation] = attribute_map
    
    
def precompute_action_list(scene_struct, s, e, period_idx, overlap_threshold):
    out = [None]*len(scene_struct['objects'])
    excluding_out = [None]*len(scene_struct['objects'])
    for obj_id, ms in scene_struct['movements'].items():
        obj_idx = scene_struct['obj_id_to_idx'][obj_id]
        for m in ms: 
            a, _, start, end = m
            if a == '_no_op': continue 
            if is_overlap(s, e, start, end, return_overlap=True) <= overlap_threshold: 
                if excluding_out[obj_idx] is None: excluding_out[obj_idx]=[]
                excluding_out[obj_idx].append(action_map[a])
            else:
                if out[obj_idx] is None: 
                    out[obj_idx]=[]
                out[obj_idx].append(action_map[a])
    
    for obj_idx, cs in scene_struct['contained_events'].items():
        for c in cs:
            start, end = c
            if is_overlap(s, e, start, end, return_overlap=True) <= overlap_threshold: 
                if excluding_out[obj_idx] is None: excluding_out[obj_idx]=[]
                excluding_out[obj_idx].append('contained')
            else:
                if out[obj_idx] is None: out[obj_idx]=[]
                out[obj_idx].append('contained')
    scene_struct['_action_list'][period_idx] = {'during': out, 'excluding': excluding_out}
