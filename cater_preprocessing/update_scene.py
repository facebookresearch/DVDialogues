"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json 
import pickle 
import glob 
import pdb
import random
import os, sys
from tqdm import tqdm 
from utils import * 
import argparse

parser = argparse.ArgumentParser()

parser.add_argument(
    '--cater_split',
    default='max2action',
    type=str,
    help='specify the cater split to run: max2action or all_actions')
parser.add_argument(
    '--scene_start_idx',
    default=0,
    type=int,
    help='specify the start index of cater videos')
parser.add_argument(
    '--scene_end_idx',
    default=10000,
    type=int,
    help="specify the end index of cater videos ")
args = parser.parse_args()

atomic_interval_threshold = 10
composition_interval_threshold = 10
overlap_threshold=5
splits = ['/workspace/hungle/data/dvd/cater/{}'.format(args.cater_split)] 
for split in splits:
    fixed_dir = 'cater/max2action/preprocessed_scenes/'
    if not os.path.isdir(fixed_dir): os.mkdir(fixed_dir)
    filenames = glob.glob(split + '/scenes/*.json')
    filenames = sorted(filenames)
    duplicate_obj_samples = 0
    for file_idx, filename in tqdm(enumerate(filenames), total=len(filenames)):
        if file_idx < args.scene_start_idx or file_idx>=args.scene_end_idx: 
            continue 
        scene = json.load(open(filename, 'r'))
        # add obj id to idx mappping
        scene['obj_id_to_idx'] = {o['instance']:idx for idx, o in enumerate(scene['objects'])}
        # precompute filter options 
        precompute_filter_options(scene)
        # precompute obj identifiers 
        duplicate_obj_samples += precompute_obj_identifiers(scene)
        
        # precompute all interlvas 
        get_all_containment_periods(scene)
        find_all_periods(scene, atomic_interval_threshold)
        find_all_compositional_periods(scene, composition_interval_threshold)
        
        # precompute relationships 
        scene['relationships'] = {}
        for idx, period in enumerate(scene['periods']): 
            e0, e1 = period 
            start = 0 if e0 is None else e0[-1]
            end = len(scene['objects'][0]['locations'])-1 if e1 is None else e1[-1]
            if end <= start:pdb.set_trace()
            sample_moment = random.sample(list(range(start,end)),1)[0]
            compute_all_relationships(scene, start, end, sample_moment, idx)
            
        scene['_action_list'] = {} 
        scene['_actions_filter_options'] = {} 
        scene['_object_identifiers_with_actions'] = {}
        scene['_minimal_object_identifiers_with_actions'] = {}
        for idx, period in enumerate(scene['all_periods']): 
            e0, e1 = period 
            start = 0 if e0 is None else e0[-1]
            end = len(scene['objects'][0]['locations'])-1 if e1 is None else e1[-1]
            if end <= start:pdb.set_trace()
            precompute_action_list(scene, start, end, idx, overlap_threshold) 
            precompute_actions_filter_options(scene, idx)
            precompute_obj_identifiers_with_action(scene, idx, 'compositional', 'during')
            
        new_filename = fixed_dir + filename.split('/')[-1].replace('json', 'pkl')
        print("Saving scene file into {}...".format(new_filename))
        pickle.dump(scene, open(new_filename, 'wb'))
        
    print('Number of samples with duplicate objects: {}/{}'.format(duplicate_obj_samples, len(filenames)))
