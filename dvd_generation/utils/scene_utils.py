"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import argparse, json, os, itertools, random, shutil
import time
import re
import pdb
import glob
from tqdm import tqdm
from utils.global_vars import *

'''
def sample_moment_by_period(scene_struct, period_idx):
    e1 = scene_struct['periods'][period_idx][0]
    e2 = scene_struct['periods'][period_idx][1]
    start = e1[-1] if e1 is not None else 0
    end = e2[-1] if e2 is not None else 301 
    moment = random.sample(range(start,end),1)[0] 
    return moment 
'''

def remove_contained_act(actions):
    if actions is not None:
        actions = [a for a in actions if 'contained' not in a]
        if len(actions)==0:
            actions = None 
    return actions 

def is_static_or_rotating(scene_struct, template, period_idx, obj_idx):
    assert template['interval_type'] == 'atomic'
    period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
    all_moves = scene_struct['_action_list'][period_idx]['during'][obj_idx]
    all_moves = remove_contained_act(all_moves)
    if all_moves is None:
        return True 
    return False 
    
    '''
    obj_id = scene_struct['objects'][obj_idx]['instance']
    ms = scene_struct['movements'][obj_id]
    moment = sample_moment_by_period(scene_struct, period_idx)
    #moment = scene_struct['relationships_moment']
    is_static = True 
    for m in ms:
        if moment>=m[2] and moment<=m[3] and (m[0]!='_no_op' and m[0]!='_rotate'):
            is_static = False 
            break
    return is_static 
    '''

def convert_to_compositional_period_idx(scene_struct, period_idx):
    period = scene_struct['periods'][period_idx]
    return scene_struct['all_periods'].index(period)

def get_snitch_idx(scene_struct):
    for idx, obj in enumerate(scene_struct['objects']):
        if obj['shape'] == 'spl':
            return idx

def is_smaller(z1, z2):
    if z1 is not None and z2 is not None and z1 != '' and z2 != '':
        sizes = ['small', 'medium', 'large']
        return sizes.index(z1) < sizes.index(z2)
    return False

'''
def get_action_by_moment(scene_struct, obj_idx, period_idx, include_moving=True):
    obj = scene_struct['objects'][obj_idx]
    movements = scene_struct['movements'][obj['instance']]
    moment = sample_moment_by_period(scene_struct, period_idx)
    moving = False 
    all_moves = set()
    for movement in movements: 
        if movement[0] == '_no_op' or moment < movement[2] or moment > movement[3]: continue 
        moving = True 
        all_moves.add(action_map[movement[0]])
    if include_moving and moving: 
            all_moves.add('moving')
    if not moving:
        all_moves.add('static')
    return all_moves
'''

def is_valid_event(period, cutoff):
    e1, e2 = period
    # to avoid ambiguous language, avoid moving/contain events
    if e1 is not None:
        if 'moving' in e1[1]: pdb.set_trace()
        if 'contain' in e1[1]: pdb.set_trace()
    if e2 is not None:
        if 'moving' in e2[1]: pdb.set_trace() 
        if 'contain' in e2[1]: pdb.set_trace() 
    # if end event is after cutoff point, skip 
    if cutoff is not None:
        if e2 is None:
            return False 
        elif e2[-1] > cutoff[-1]:
            return False    
    # avoid sampling whole video (already simulated whole video using probability sampling) 
    if e1 is None and e2 == cutoff: 
        return False
    elif e1 is None:
        return True 
    elif e2 == cutoff:
        return True
    else:
        # using interval based on the same object only
        if e1[0] != e2[0]:
            return False
        return True

def is_containment_event(period, cutoff):
    e1, e2 = period
    if e1 is not None:
        return 'contain' in e1[1]
    elif e2!= cutoff:
        return 'contain' in e2[1] 
    else:
        pdb.set_trace()

def is_obj_of_period(obj_idx, period):
    e1, e2 = period 
    if e1 is None and e2 is None: 
        return False 
    elif e1 is None: 
        return e2[0] == obj_idx 
    elif e2 is None: 
        return e1[0] == obj_idx 
    else:
        if e1[0] != e2[0]: 
            return False 
        else:
            return e1[0] == obj_idx 
    
def get_period_obj(period, cutoff):
    e1, e2 = period
    if e1 is None and e2 == cutoff:
        pdb.set_trace()
    if e1 is None:
        return e2[0]
    if e2 == cutoff:
        return e1[0]
    else:
        assert e1[0]==e2[0]
        return e1[0]
    
def is_overlap(s1, e1, s2, e2, return_overlap=False):
    if return_overlap:
        if s2<e1 and s1<e2:
            return min(e1,e2)-max(s1,s2)
        else:
            return 0 
    return s2<e1 and s1<e2

def get_identifier(params, state, param_name_to_type):
    curr_identifier = []
    for p in params: 
        if p not in state['vals']: pdb.set_trace()
        val = state['vals'][p]
        val = None if val=='' else val 
        if param_name_to_type[p]=='Shape' and val=='thing': 
            val=None
        curr_identifier.append(val)
    curr_identifier = tuple(curr_identifier)
    return curr_identifier 

def find_event_ordinal(event, scene, cutoff):
    all_events = scene['events']
    obj, action, ordinal, time = event 
    action_type = action.split('_')[1]
    sim_events = []
    cutoff_t = cutoff[-1] if cutoff is not None else len(scene['objects'][0]['locations'])-1
    action_period = []
    for e in all_events:
        o, a, od, t = e
        if t > cutoff_t: 
            continue 
        at = a.split('_')[1]
        if at == action_type and o == obj and od == ordinal:
            action_period.append(t)
        if 'start' in a:  
            if o == obj and at == action_type:
                sim_events.append(e)
    assert len(sim_events)>0 
    # action period is till after cutoff 
    if len(action_period)!=2: 
        action_period.append(-1)
    action_period = sorted(action_period)
    if ordinal == len(sim_events) and ordinal==1: 
        return 'only', tuple(action_period)
    if ordinal == len(sim_events):
        return 'last', tuple(action_period)
    return ordinal, tuple(action_period)
            
    
