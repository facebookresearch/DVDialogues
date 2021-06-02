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
from utils.global_vars import cutoff_interval_threshold
from utils.scene_utils import convert_to_compositional_period_idx
#from utils import sample_moment_by_period

def sample_cutoff(scene_struct, prior_cutoff=None, used_periods=None):
    found_cutoff = False 
    for trial in range(100):
        cutoff_e = random.choice(random.choice(scene_struct['grouped_events']))
        if 'moving' in cutoff_e[1] or 'contain' in cutoff_e[1]: 
            continue 
        if used_periods is not None and (used_periods[-1][0], cutoff_e) not in scene_struct['all_periods']:
            continue 
        cutoff_t = cutoff_e[-1]
        if prior_cutoff is not None:
            prior_cutoff_t = prior_cutoff[-1] 
        else:
            prior_cutoff_t = 0 
        if (cutoff_t-prior_cutoff_t) > cutoff_interval_threshold \
            and len(scene_struct['objects'][0]['locations'])-1-cutoff_t>cutoff_interval_threshold:
            found_cutoff = True
            break
            
    if found_cutoff:
        return cutoff_e
    return None

def find_filter_options(object_idxs, scene_struct, metadata):
    # Keys are tuples (size, color, shape, material) (where some may be None)
    # and values are lists of object idxs that match the filter criterion

    #if '_filter_options' not in scene_struct:
    #    precompute_filter_options(scene_struct, metadata)

    attribute_map = {}
    object_idxs = set(object_idxs)
    for k, vs in scene_struct['_filter_options'].items():
        attribute_map[k] = sorted(list(object_idxs & vs))
    return attribute_map

'''
def find_action_filter_options(object_idxs, scene_struct, metadata, period_idx):
    # Keys are tuples (size, color, shape, material) (where some may be None)
    # and values are lists of object idxs that match the filter criterion

    #if '_action_filter_options' not in scene_struct:
    #    precompute_action_filter_options(scene_struct, metadata, period_idx)
    
    attribute_map = {}
    object_idxs = set(object_idxs)
    for k, vs in scene_struct['_action_filter_options'][period_idx].items():
        attribute_map[k] = sorted(list(object_idxs & vs))
    return attribute_map
'''

def find_actions_filter_options(object_idxs, scene_struct, metadata, template, period_idx, period_relation='during'):
    # Keys are tuples (size, color, shape, material) (where some may be None)
    # and values are lists of object idxs that match the filter criterion

    #if '_action_filter_options' not in scene_struct:
    #    precompute_action_filter_options(scene_struct, metadata, period_idx)
    if template['interval_type'] == 'atomic': 
        period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
    attribute_map = {}
    object_idxs = set(object_idxs)
    for k, vs in scene_struct['_actions_filter_options'][period_idx][period_relation].items():
        attribute_map[k] = sorted(list(object_idxs & vs))
    return attribute_map

def add_empty_filter_options(attribute_map, metadata, num_to_add, with_action=True):
    # Add some filtering criterion that do NOT correspond to objects
    if metadata['dataset'] == 'CLEVR-v1.0':
        attr_keys = ['Action'] if with_action else []
        attr_keys += ['Size', 'Color', 'Material', 'Shape']
    else:
        assert False, 'Unrecognized dataset'

    attr_vals = [metadata['types'][t] + [None] for t in attr_keys]
    #if '_filter_options' in metadata:
    #    attr_vals = metadata['_filter_options']

    target_size = len(attribute_map) + num_to_add
    unique_snitch_options = [(None, 'gold', None, None), (None, None, None, 'spl')]
    while len(attribute_map) < target_size:
        k = tuple([random.choice(v) for v in attr_vals])
        if 'gold' in k or 'spl' in k:
            if with_action:
                if k[1:] not in unique_snitch_options: continue
            else:
                if k not in unique_snitch_options: continue
        if with_action and 'sphere' in k and 'rotating' in k: continue 
        if k not in attribute_map:
            attribute_map[k] = []

def find_relate_filter_options(object_idx,
                               scene_struct, metadata, template,
                               unique=False, include_zero=False, with_action=False,
                               period_idx=-1, trivial_frac=0.1):
    options = {}
    # TODO: Why object_idx? always int in this case?
    #if with_action:
    #    if '_action_filter_options' not in scene_struct:
    #        precompute_action_filter_options(scene_struct, metadata, period_idx)
    #else:
    #    if '_filter_options' not in scene_struct:
    #        precompute_filter_options(scene_struct, metadata)

    # TODO: Right now this is only looking for nontrivial combinations; in some
    # cases I may want to add trivial combinations, either where the intersection
    # is empty or where the intersection is equal to the filtering output.
    if with_action:
        if template['interval_type'] == 'atomic': 
            new_period_idx = convert_to_compositional_period_idx(scene_struct, period_idx)
        filter_options = scene_struct['_actions_filter_options'][new_period_idx]['during']  
    else:
        filter_options = scene_struct['_filter_options']
    
    trivial_options = {}
    for relationship in scene_struct['relationships'][period_idx]:
        if relationship in ['above', 'below']:
            continue  #and not args.above_below_relate: continue
        if relationship in ['containing', 'contained']:
            continue 
            
        related = set(scene_struct['relationships'][period_idx][relationship][object_idx])
        
        for filters, filtered in filter_options.items():
            intersection = related & filtered
            trivial = (intersection == filtered)
            if unique and len(intersection) != 1: continue
            if not include_zero and len(intersection) == 0: continue
            if trivial:
                trivial_options[(relationship, filters)] = sorted(
                    list(intersection))
            else:
                options[(relationship, filters)] = sorted(list(intersection))
    #pdb.set_trace()
    N, f = len(options), trivial_frac
    num_trivial = int(round(N * f / (1 - f)))
    trivial_options = list(trivial_options.items())
    random.shuffle(trivial_options)
    for k, v in trivial_options[:num_trivial]:
        options[k] = v

    return options

def get_filter_options(metadata, scene_struct, template, answer, next_node, period_idx):
    if next_node['type'].startswith('relate_filter') or next_node['type'].startswith('relate_action_filter'):
        unique = (next_node['type'] == 'relate_filter_unique') or (next_node['type'] == 'relate_action_filter_unique')
        include_zero = (next_node['type'] == 'relate_filter_count' or next_node['type'] == 'relate_filter_exist' \
                    or next_node['type'] == 'relate_action_filter_count' or next_node['type'] == 'relate_action_filter_exist')
        with_action = 'action' in next_node['type']
        filter_options = find_relate_filter_options(answer, scene_struct, 
                                                    metadata, template, 
                                                    unique = unique, include_zero = include_zero,
                                                    with_action = with_action,
                                                    period_idx = period_idx)
    else:            
        #if 'actions' in next_node['type']:
        #    filter_options = find_actions_filter_options(answer, scene_struct, metadata, period_idx=period_idx)
        #elif 'action' in next_node['type']:
        
        if 'actions' in next_node['type']: 
            if template['interval_type'] != 'compositional': pdb.set_trace()
        elif 'action' in next_node['type']:
            if template['interval_type'] != 'atomic': pdb.set_trace()
                
        if 'action' in next_node['type']:
            filter_options = find_actions_filter_options(answer, scene_struct, metadata, 
                                                        template, period_idx=period_idx)
        else:
            filter_options = find_filter_options(answer, scene_struct, metadata)
        
        if next_node['type'] == 'filter':
            # Remove null filter
            filter_options.pop((None, None, None, None), None)
        elif next_node['type'] in ['action_filter', 'actions_filter']:
            filter_options.pop((None, None, None, None, None), None)
        
        if next_node['type'] in ['filter_unique', 'action_filter_unique', 'actions_filter_unique']:
            # Get rid of all filter options that don't result in a single object
            filter_options = {k: v for k, v in filter_options.items() if len(v) == 1}
        else:
            # Add some filter options that do NOT correspond to the scene
            if next_node['type'] in ['filter_exist', 'action_filter_exist', 'actions_filter_exist']:
                # For filter_exist we want an equal number that do and don't
                num_to_add = len(filter_options)
            elif next_node['type'] in \
                ['filter_count','filter', 'action_filter_count', 'action_filter', 'actions_filter_count', 'actions_filter']:
                # For filter_count add nulls equal to the number of singletons
                num_to_add = sum(1 for k, v in filter_options.items() if len(v) == 1)
            add_empty_filter_options(filter_options, metadata, num_to_add, with_action='action' in next_node['type'])
    return filter_options
