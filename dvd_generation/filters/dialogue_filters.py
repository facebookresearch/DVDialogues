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
from utils.dialogue_utils import *
from utils.scene_utils import *
from utils.global_vars import *

def create_relate_template(prior_template, turn_dependencies, used_periods, scene_struct, synonyms):
    template = copy.deepcopy(prior_template)
    relate_text = random.choice(synonyms[turn_dependencies['spatial']])
    template['text'] = ['what about {} it ?'.format(relate_text), 'how about {} it ?'.format(relate_text)]
    
    prior_period = template['used_periods'][-1]
    used_periods.append(prior_period)
    
    curr_interval = template['interval_type']
    curr_periods = scene_struct[intervals_to_periods[curr_interval]] 
    period_idx = curr_periods.index(prior_period)
    
    template['used_periods'] = copy.deepcopy(used_periods)
    
    return template, period_idx

def sample_unknown_spatial(dialogue, turn_dependencies):
    for n in dialogue[-1]['program']:
        if n['type'] == 'relate':
            prior_relate = n['side_inputs'][0] 
            break
    unknown_relates = copy.deepcopy(relate_attrs)
    unknown_relates.remove(prior_relate)
    sampled_relate = random.choice(unknown_relates)
    turn_dependencies['spatial'] = sampled_relate
    return sampled_relate

def create_query_template(prior_template, turn_dependencies, used_periods):
    template = copy.deepcopy(prior_template)
    
    template['interval_type'] = 'none'
    attr = node_type_to_attribute[turn_dependencies['attribute']]
    attr = attribute_to_text[attr]
    template['text'] = ['what about its {} ?'.format(attr), 'how about its {} ?'.format(attr)]
    
    template['nodes'] = template['nodes'][-2:]
    template['nodes'][0]['type'] = 'unique_obj_ref'
    template['nodes'][0]['side_inputs'] = []
    template['nodes'][0]['inputs'] = []
    template['nodes'][1]['inputs'] = [0]
    template['nodes'][1]['type'] = turn_dependencies['attribute']
    
    template['unique_obj'] = [0, template['nodes'][0]]
    template['all_unique_objs'] = [[0,template['nodes'][0]]]
    assert template['answer_obj'] is None 
    
    used_periods.append(None)
    template['used_periods'] = copy.deepcopy(used_periods)
    
    return template 

def sample_unknown_attr(dialogue, template, turn_dependencies):
    prior_output_obj = dialogue[-1]['program'][-2]['_output']
    prior_output_obj_attr = template['used_objects'][prior_output_obj]
    unknown_attrs = []
    for a in identifier_attrs:
        if a in prior_output_obj_attr:
            if a is None or a == '': 
                pdb.set_trace()
            continue 
        unknown_attrs.append(a) 
    if len(unknown_attrs)==0: 
        return None
    sampled_attr = random.choice(unknown_attrs)
    turn_dependencies['attribute'] = attribute_to_node_type[sampled_attr]
    return sampled_attr
    

def update_period(template, scene_struct, turn_dependencies, used_periods, cutoff):
    #last_template = dialogue[-1]['template']
    prior_period = template['used_periods'][-1]
    new_period = (prior_period[0], cutoff)    
    #prior_interval = last_template['interval_type']
    curr_interval = template['interval_type']
    curr_periods = scene_struct[intervals_to_periods[curr_interval]] 
    if new_period not in curr_periods:
        pdb.set_trace()
    period_idx = curr_periods.index(new_period) 
    template['used_periods'].append(new_period)
    used_periods.append(new_period)
    turn_dependencies['temporal'] = 'video_update'
    return period_idx

def sample_period(dialogue, template, scene_struct, turn_dependencies, metadata, used_periods):
    last_unique_obj_idx = template['prior_unique_obj']
    cutoff = template['cutoff']
    
    if len(dialogue)==0 or template['interval_type'] == 'none' or \
        (len(dialogue)>0 and dialogue[-1]['template']['interval_type'] == 'none'):
        period_idx = sample_period_idx(dialogue, template, scene_struct, used_periods, 
                                       turn_dependencies, last_unique_obj_idx) 
        template['used_periods'] = copy.deepcopy(used_periods)
        return period_idx 
    
    else:
        last_template = dialogue[-1]['template']
        prior_period = last_template['used_periods'][-1]
        #original_period = copy.deepcopy(prior_period)
        prior_interval = last_template['interval_type']
        last_question_type = last_template['nodes'][-1]['type']
        curr_interval = template['interval_type']
        curr_question_type = template['nodes'][-1]['type']        
        curr_periods = scene_struct[intervals_to_periods[curr_interval]]
        # special tags fo special cases e.g. among those actions ..., during this activities, ....
        tag, prior_period = sample_among_prior_actions(dialogue, scene_struct, prior_period, cutoff)
        if tag == '': tag, prior_period = sample_unique_answer_action(dialogue, scene_struct, prior_period, cutoff)
        if tag != '':
            template['new_prior_period'] = prior_period
        while(True):
            while(True): 
                sampled = random.choice(metadata['turn_dependencies']['temporal'])
                # avoid cases without temporal localization (i.e. none) when tag is not empty 
                if sample_by_prop(not_none_temporal_dependency_p) and tag!='' and sampled=='none':
                    continue
                break 

            turn_dependencies['temporal'] = sampled if sampled=='none' else tag+sampled
            prior_temporal_dependency = dialogue[-1]['turn_dependencies']['temporal']
            
            if sampled == 'none':
                period_idx = sample_period_idx(dialogue, template, scene_struct, used_periods, 
                                               turn_dependencies, last_unique_obj_idx)
                template['used_periods'] = copy.deepcopy(used_periods)
                return period_idx 
            
            elif sampled == 'during': 
                # Avoid asking count/exist if previous turn is also count/exist 
                # this is to avoid redudant questions being asked in contiguous turns 
                if 'count' in last_question_type or 'exist' in last_question_type \
                    and ('count' in curr_question_type or 'exist' in curr_question_type):
                    continue 
                # Limit to one repetition of prior period only to avoid confusion 
                if prior_temporal_dependency in ['during', 'excluding', 'before', 'after', 'video_update']: 
                    continue  
                # if prior period is during a whole video, skip
                if prior_period == (None, cutoff):
                    continue 
                if prior_period not in curr_periods:
                    # atomic interval set is a subset of compositional interval set, so it's okay to skip
                    if prior_interval == 'compositional' and curr_interval == 'atomic': continue 
                    pdb.set_trace()
                period_idx = curr_periods.index(prior_period)
                used_periods.append(prior_period)
                template['used_periods'] = copy.deepcopy(used_periods)
                return period_idx
            
            elif sampled in ['before', 'after']:
                # to avoid confusion, before and after cannot go after an excluding, before, after type of interval 
                if prior_temporal_dependency in ['excluding', 'before', 'after', 'during', 'video_update']: 
                    continue 
                # if prior period is during a whole video, skip
                if prior_period == (None, cutoff):
                    continue 
                period_idx, new_period = sample_relative_period(curr_periods, used_periods, prior_period, 
                                                                curr_interval, sampled, cutoff, scene_struct)
                if period_idx == -1: continue 
                used_periods.append(new_period)
                template['used_periods'] = copy.deepcopy(used_periods)
                return period_idx 
            
            '''
            elif sampled == 'excluding':
                # TODO: implement excluding when cutoff is not None ? 
                if cutoff is not None:
                    continue 
                # Limit to one repetition of prior period only
                if prior_temporal_dependency in ['during', 'before', 'after', 'excluding']: 
                    continue       
                # if prior period is during a whole video, skip
                if prior_period == (None, cutoff):
                    continue 
                # excluding is only for compositional interval 
                if curr_interval == 'atomic': 
                    continue 
                if prior_period not in curr_periods:
                    pdb.set_trace()
                period_idx = curr_periods.index(prior_period)
                used_periods.append(prior_period)
                template['used_periods'] = copy.deepcopy(used_periods)
                return period_idx   
            '''
            
def find_all_unique_objects(dialogue, template, scene_struct, used_objects):
    template['sampled_ans_object'] = -1 
    
    if len(dialogue)==0: 
        template['used_objects'] = {}
        template['ans_objects'] = []
        return 
    
    last_turn = dialogue[-1]
    last_turn_dependencies = last_turn['turn_dependencies']
    prior_state = last_turn['state']
    last_template = last_turn['template']
    prior_objs = last_template['all_unique_objs'] 
    prior_ans_obj = last_template['answer_obj']
    last_period = last_template['used_periods'][-1]
    curr_turn_pos = len(dialogue)
    template['ans_objects'] = []

    found_unique_ans = False 
    # Case 1: previous dialogue turn is an exist (e.g. Is there...) or count (e.g. How many...)
    if prior_ans_obj is not None and (last_turn['answer']):
        obj_id, obj_attr, obj_ids = find_unique_answer_obj(last_turn, prior_state, prior_ans_obj)
        if obj_id!=-1: 
            update_unique_object(obj_id, obj_attr, used_objects, curr_turn_pos)
            found_unique_ans = True 
        template['ans_objects'] = obj_ids
       
        #find_answer_objs(last_turn, prior_state, prior_ans_obj)
            
     # Case 2: the unique object came from temporal dependency
    if last_template['interval_type']!='none' and 'none' in last_turn_dependencies['temporal'] \
        and last_turn_dependencies['spatial']=='none': 
        e1, e2 = last_period
        if e1 is not None or e2 != last_template['cutoff']: 
            if last_template['temporal_obj_attr'] is not None: 
                update_unique_object(last_template['temporal_obj_id'], 
                                     last_template['temporal_obj_attr'], used_objects, curr_turn_pos)
            #if last_template['temporal_obj_attr_2'] is not None:
            #    update_unique_object(last_template['temporal_obj_id_2'], 
            #                         last_template['temporal_obj_attr_2'], used_objects, curr_turn_pos)
        '''
        e1, e2 = last_period
        found_unique = False 
        if e1 is not None:
            obj_id = e1[0]
            found_unique = True
        elif e2 != template['cutoff']:
            obj_id = e2[0]
            found_unique = True
        if found_unique:
            if 'temporal_obj_attr' not in last_template:
                pdb.set_trace()
            update_unique_object(obj_id, last_template['temporal_obj_attr'], used_objects)
         '''
        
    # Case 3: all other unique objects  from the last turn 
    if last_turn_dependencies['attribute'] != 'none':
        obj_id = prior_state['nodes'][0]['_output']
        attr_type = node_type_to_attribute[last_turn_dependencies['attribute']]                             
        attr = prior_state['nodes'][1]['_output']
        obj_attr = {}
        obj_attr[attr_type] = attr
        update_unique_object(obj_id, obj_attr, used_objects, curr_turn_pos)                            
    else:
        for o in prior_objs:
            obj_id, obj_attr = find_unique_obj(last_turn, prior_state, o)
            update_unique_object(obj_id, obj_attr, used_objects, curr_turn_pos)
        
    # Case 4: sample an object from a count (e.g. How many...) where result > 1 (among them, there is a...)
    if prior_ans_obj is not None and not found_unique_ans:
        obj_ids, obj_id, obj_attr, sampled_obj_attr = sample_unique_answer_obj(last_turn, prior_state, prior_ans_obj, used_objects, scene_struct)
        if obj_id != -1:
            #update_unique_object(obj_id, obj_attr, used_objects)
            template['sampled_ans_object_attr_ref'] = obj_attr
            template['prior_ans_object_group'] = obj_ids
            template['sampled_ans_object'] = obj_id 
            template['sampled_ans_object_attr'] = sampled_obj_attr 
        
    template['used_objects'] = copy.deepcopy(used_objects)
    return 

def precompute_unique_dialogue_object_identifiers(template):
    used_objects = template['used_objects'] 
    if len(used_objects)==0: 
        return {}
    attribute_map = precompute_object_filter_options(used_objects)
    output, minimal_output = precompute_obj_identifiers(attribute_map, used_objects)
    template['_dial_object_identifiers'] = output
    template['_dial_minimal_object_identifiers'] = minimal_output 
    #return duplicate_objs    
                    
def sample_prior_unique_object(dialogue, template, cutoff): #, turn_dependencies, metadata):
    if len(dialogue)==0:
        template['prior_unique_obj'] = -1 
        return 
    
    last_turn = dialogue[-1]
    prior_state = last_turn['state']
    last_template = last_turn['template']
    prior_obj = last_template['unique_obj'] 
    all_prior_objs = last_template['all_unique_objs']
    prior_ans_obj = last_template['answer_obj']
    used_objects = template['used_objects']
    
    # Case 1: previous dialogue turn is an exist (e.g. Is there...) or count (e.g. How many...)
    if prior_ans_obj is not None:
        if template['sampled_ans_object']!=-1: 
            template['prior_unique_obj'] = template['sampled_ans_object']
            template['prior_unique_obj_attr'] = template['sampled_ans_object_attr']
            return 
        
        # ask further about resulting object if count question result is 1/ exist question result is True
        # else, there is no prior unique obj
        template['prior_unique_obj'], template['prior_unique_obj_attr'], _ = find_unique_answer_obj(
            last_turn, prior_state, prior_ans_obj, used_objects)
        return

    # Case 2: the only unique object came from temporal dependency
    if prior_obj is None and len(all_prior_objs)==0:
        # temporal phrase is not during/before/after/among
        if last_template['interval_type']!='none' and 'none' in last_turn['turn_dependencies']['temporal']:
            e1, e2 = last_template['used_periods'][-1] 
            # interval that involves more than one object 
            if e1 is not None and e2 != cutoff and e1[0] != e2[0]:
                template['prior_unique_obj'] = -1
                return 
            if e1 is not None:
                template['prior_unique_obj'], template['prior_unique_obj_attr'] = e1[0], used_objects[e1[0]]
                return
            elif e2 != cutoff:
                template['prior_unique_obj'], template['prior_unique_obj_attr'] = e2[0], used_objects[e2[0]]
                return 
            else:
                template['prior_unique_obj'] = -1 
                return
        else:
            template['prior_unique_obj'] = -1 
            return
    
    if prior_obj is None:
        template['prior_unique_obj'] = -1 
        return 
    
    # Only one prior object (nonambiguous) from the last turn 
    template['prior_unique_obj'], template['prior_unique_obj_attr'] = find_unique_obj(
        last_turn, prior_state, prior_obj, used_objects)
    return 

def sample_earlier_unique_object(dialogue, template): #, turn_dependencies, metadata):
    if len(dialogue)==0 or template['ref_remark'] == 'no_reference': 
        template['earlier_unique_obj'] = -1 
        return 

    used_objects = template['used_objects']
    curr_objects = template['all_unique_objs']
    
    if len(curr_objects)==0 or len(used_objects)==0: 
        template['earlier_unique_obj'] = -1
        return 
    
    identifiers =  template['_dial_minimal_object_identifiers']
    
    while(True):
        curr_object = random.choice(curr_objects)
        if len(curr_object)==3 and curr_object[2]=='ans':
            continue
        break

    past_turns = list(range(1, len(dialogue)+1))
    random.shuffle(past_turns)
    past_objects = copy.deepcopy(list(used_objects))
    random.shuffle(past_objects) 
    found_earlier = False 
    for turn in past_turns:
        for earlier_obj_id in past_objects:
            if identifiers[earlier_obj_id] != [None] and used_objects[earlier_obj_id]['original_turn']==turn: 
                found_earlier = True 
                break
        if found_earlier: break 
    
    '''
    temp = copy.deepcopy(list(used_objects))
    pdb.set_trace()
    random.shuffle(temp)
    found_earlier = False 
    for earlier_obj_id in temp:
        #earlier_obj_id = random.choice(list(used_objects))
        if identifiers[earlier_obj_id] != [None]:
            found_earlier = True 
            break       
    '''
    
    if not found_earlier: 
        template['earlier_unique_obj'] = -1
        return 

    identifier_attrs = curr_object[1]['side_inputs']
    strip_identifier_attrs = [strip_attr_key(a) for a in identifier_attrs]
    identifier = random.choice(identifiers[earlier_obj_id])
    if identifier == (None,None,None,None):pdb.set_trace()
    if len(identifier_attrs)!=4: pdb.set_trace()
    obj_attr = {}
    obj_attr_map = {k:v for k,v in zip(strip_identifier_attrs,identifier_attrs)}
    for idx, i in enumerate(identifier):
        if i is None:
            if idx == len(identifier)-1: # Shape
                val = 'thing'
            else:
                val = ''
        else:
            val = i
        obj_attr[strip_identifier_attrs[idx]] = val

    template['earlier_unique_obj'] = earlier_obj_id
    template['earlier_unique_obj_attr'] = obj_attr
    template['earlier_unique_obj_attr_map'] = obj_attr_map
    template['earlier_unique_obj_node'] = curr_object[1]

    return 

def is_valid_dialogue(dialogue, scene_struct):
    nb_dependencies = {'all': 0, 'temporal': 0, 'object': 0, 'attribute': 0, 'spatial': 0}
    nb_contains = 0 
    nb_amongs = 0
    nb_spatial = 0 
    nb_cutoff = 0 
    nb_freq_seq_q = 0 
    #nb_excluding = 0 
    found_diff_ans_after_cutoff = False
    
    for t_idx, t in enumerate(dialogue): 
        curr_dependencies = t['turn_dependencies']
        if len([d for d in curr_dependencies.values() if d!='none']) > 0:
            nb_dependencies['all'] += 1
        nb_dependencies['object'] += 1 if (curr_dependencies['object']!='none' or \
                                'unique' in curr_dependencies['temporal']) else 0
        nb_dependencies['temporal'] += 1 if curr_dependencies['temporal']!='none'else 0
        nb_dependencies['attribute'] += 1 if 'none' not in curr_dependencies['attribute'] else 0
        nb_dependencies['spatial'] += 1 if 'none' not in curr_dependencies['spatial'] else 0

        if 'contain' in t['question']:
            nb_contains += 1 
        if 'one_hop' in t['template_filename']:
            nb_spatial += 1 
        if curr_dependencies['temporal'] == 'video_update':
            nb_cutoff += 1 
            curr_ans = t['answer']
            prior_ans = dialogue[t_idx-1]['answer']
            if curr_ans != prior_ans:
                found_diff_ans_after_cutoff = True
        if 'among' in t['question']:
            nb_amongs += 1 
        if t['template_filename'] == 'zero_hop_5.json' and t['question_family_index'] in [12,13]:
            nb_freq_seq_q += 1 
        #if curr_dependencies['temporal'] == 'excluding':
        #    nb_excluding += 1 
        
    
    #print(nb_contains, nb_spatial, nb_cutoff, nb_amongs, found_diff_ans_after_cutoff)
    #print(nb_dependencies)
    match = 0 
    if nb_amongs>0: match += 1 
    #if (not scene_struct['has_contain'] or nb_contains>0): match += 1 
    if found_diff_ans_after_cutoff: match += 1 
    #if nb_freq_seq_q>0: match += 1 
        
    #if nb_dependencies['object']>5: match += 1 
    if nb_dependencies['temporal']>=len(dialogue)*0.3: match += 1 
    #if nb_dependencies['attribute']>0: match += 1 
    if nb_dependencies['spatial']>0: match += 1 
    if nb_dependencies['all']>=len(dialogue)-1: match += 1 
     
    if match == 5: 
        return True 

    return False 



