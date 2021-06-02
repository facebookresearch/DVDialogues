"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json, os, itertools, random, shutil, glob
import pdb 
import pickle as pkl
from tqdm import tqdm

def load_data(args): 
    with open(args.metadata_file, 'r') as f:
        metadata = json.load(f)
        dataset = metadata['dataset']
    functions_by_name = {}
    for f in metadata['functions']:
        functions_by_name[f['name']] = f
    metadata['_functions_by_name'] = functions_by_name

    # Load templates from disk
    # Key is (filename, file_idx)
    num_loaded_templates = 0
    templates = {}
    for fn in os.listdir(args.template_dir):
        if not fn.endswith('_6.json'): continue
        with open(os.path.join(args.template_dir, fn), 'r') as f:
            base = os.path.splitext(fn)[0]
            for i, template in enumerate(json.load(f)):
                num_loaded_templates += 1
                key = (fn, i)
                templates[key] = template
    print('Read %d templates from disk' % num_loaded_templates)

    with open(args.cater_label_file, 'r') as f:
        lines = f.readlines()
        label_vid_ls = []
        for line in lines:
            label_vid_ls.append(line.split()[0])
    
    # Read file containing input scenes
    all_scenes = []
    scene_files = glob.glob(args.input_scene_file + '/*.pkl')
    split = args.input_scene_file.split('/')[-3]
    cater_split = args.cater_label_file.split('/')[-1].split('.')[0]
    #found = False
    for scene_idx, scene_file in tqdm(enumerate(scene_files), total=len(scene_files)):
        #if 'CATER_new_000116' in scene_file: 
        #    found = True 
        #    continue
        #if not found: continue 
        #if scene_idx<args.scene_start_idx: continue  
        #if '000106' not in scene_file:
        #    continue 
        if scene_file.split('/')[-1].replace('pkl', 'avi') in label_vid_ls:
            all_scenes.append(scene_file)
        
        #if args.num_scenes > 0 and len(all_scenes) == args.num_scenes: break
    
    all_scenes = sorted(all_scenes)
    #selected_scenes = []
    #for idx, scene in enumerate(all_scenes): 
    #    if scene_idx<args.scene_start_idx: continue 
    #    selected_scenes.append(scene)
    #    if args.num_scenes > 0 and len(selected_scenes) == args.num_scenes: break 
    
    #if args.num_scenes <= 0:
    #    assert len(all_scenes) == len(label_vid_ls), "Error in loading data by CATER label split"

    # Read synonyms file
    with open(args.synonyms_json, 'r') as f:
        synonyms = json.load(f)
    
    return metadata, templates, all_scenes, synonyms, split, cater_split
