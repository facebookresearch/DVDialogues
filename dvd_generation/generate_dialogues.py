"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

from __future__ import print_function
import json, os, itertools, random, shutil, copy
import time
import re
import pdb
import glob
from tqdm import tqdm
import pickle as pkl
import numpy as np

from utils.configs import * 
from utils.utils import * 
from utils.data_loader import load_data
from filters.dialogue_filters import *
from filters.scene_filters import *
from simulators.template_dfs import *


def main(args):
    metadata, templates, all_scenes, synonyms, split, cater_split = load_data(args)        
    template_counts, template_answer_counts = reset_counts(metadata, templates)
    #has_obj_for_reference(templates)
    #gen_dials = json.load(open('/mnt/vol/gfsfblearner-carolina/users/hle/output/human_test/ahmad/CATER_new_000106.json'))
    
    scene_count = 0
    no_output_count = 0
    turn_dependency_count = {}
    it = tqdm(enumerate(all_scenes), total=len(all_scenes))
    
    for i, scene_file in it:
        if i < args.scene_start_idx: continue 
        if i == args.scene_end_idx: break 
        
        scene = pkl.load(open(scene_file, 'rb'))
        
        nb_unique_objs = [o for o in scene['_minimal_object_identifiers'] if o is not None]
        if len(nb_unique_objs) == 1:
            print("Video ID {} only has one unique obj {} ==> Skip this".format(scene_file, len(nb_unique_objs)))
            continue
            
        dialogues = []
        
        scene_fn = scene['image_filename']
        scene_struct = scene
        if args.verbose: print('starting image %s (%d / %d)' % (scene_fn, i + 1,len(all_scenes)))

        if scene_count % args.reset_counts_every == 0:
            print('resetting counts')
            template_counts, template_answer_counts = reset_counts(metadata, templates)
        scene_count += 1

        # Order templates by the number of questions we have so far for those
        # templates. This is a simple heuristic to give a flat distribution over
        # templates.
        templates_items = list(templates.items())
        
        for dial in range(args.dialogues_per_image):
            #templates_items = sorted(templates_items, key=lambda x: template_counts[x[0][:2]])
            #while(True):
            
            valid_dial = False
            for trial in range(max_dial_sampling_attempts): 
                it.set_description("Processing video# {} trial# {} no_output# {}".format(i, trial, no_output_count))
                
                num_instantiated = 0
                turn_dependencies_original = {'temporal': 'none', 
                                              'object': 'none', 
                                              'attribute': 'none',
                                              'spatial': 'none'}
                
                dialogue = [] 
                used_periods = []
                used_objects = {} 
                used_templates = set()
                cutoff = sample_cutoff(scene_struct)
                
                #dialogue = [gen_dials[0][0]]
                #used_periods = dialogue[-1]['template']['used_periods']
                #used_periods[0][0] = tuple(used_periods[0][0])
                #used_periods[0][1] = tuple(used_periods[0][1])
                #used_periods[0] = tuple(used_periods[0])
                #used_objects = dialogue[-1]['template']['used_objects']
                #cutoff = tuple(dialogue[-1]['template']['cutoff'])
                #pdb.set_trace()
                
                last_turn, last_template, last_dependencies, last_state, last_period = None, None, None, None, None
                
                while(num_instantiated != args.turns_per_dialogue):
                    #if num_instantiated == args.max_turns_per_dialogue:
                    #    break 
                    prior_used_periods = copy.deepcopy(used_periods)
                    prior_used_objects = copy.deepcopy(used_objects)
                    prior_used_templates = copy.deepcopy(used_templates) 
                    turn_dependencies = copy.deepcopy(turn_dependencies_original)
                    prior_cutoff = copy.deepcopy(cutoff) 
                    #key, template = random.choice(templates_items[:args.turns_per_dialogue])
                    key, template_original = random.choice(templates_items)
                    
                    if len(dialogue)>0: 
                        last_turn = dialogue[-1]
                        last_template = last_turn['template']
                        last_dependencies = last_turn['turn_dependencies']  
                        last_state = last_turn['state']
                        last_period = used_periods[-1] 
                        last_temporal_program = last_turn['temporal_program']
                        last_earlier_obj_program = last_turn['earlier_object_program']
                        last_unique_obj_program = last_turn['last_object_program']
                    
                    # Update video segment to a new cutoff point, keep the question from prior turn
                    # in case of interval_type == None, skip
                    # limit to one repetition of video update 
                    if sample_by_prop(video_cutoff_p) \
                        and len(used_periods)>0 and cutoff is not None \
                        and last_period is not None and last_period[-1] == cutoff \
                        and last_dependencies['temporal']!='video_update' \
                        and last_template['interval_type']!='atomic' \
                        and last_template['nodes'][-1]['type'] not in node_type_to_attribute \
                        and not ('exist' in last_template['nodes'][-1]['type'] and  last_turn['answer']) \
                        and not (last_template['nodes'][-1]['type']=='query_action_order' and last_turn['answer']!='no action'): 
                        
                        template = copy.deepcopy(dialogue[-1]['template'])
                        fn, idx = last_turn['template_filename'], last_turn['question_family_index']
                        find_all_unique_objects(dialogue, template, scene_struct, used_objects)
                        
                        if template['unique_obj'] is not None: 
                            # remove last unique object in this turn to avoid confusion 
                            template['unique_obj'] = None
                        if template['used_objects'] != used_objects:
                            pdb.set_trace()
                           
                        cutoff = sample_cutoff(scene_struct, cutoff, used_periods)
                        template['cutoff'] = cutoff
                        period_idx = update_period(template, scene_struct, turn_dependencies, used_periods, cutoff)
                                                
                        last_state = dialogue[-1]['state']
                        states, outputs = transfer_template(
                            scene_struct, template, metadata,
                            template_answer_counts[(fn, idx)],
                            synonyms, period_idx, turn_dependencies, last_state)
                        ts, qs, ans, tps, eops, lops = outputs
                        assert eops == [[]] and lops == [[]]
                        eops = [copy.deepcopy(last_earlier_obj_program)]
                        lops = [copy.deepcopy(last_unique_obj_program)]
                    
                    # Attribute dependency e.g. how about its shape? what about its material? 
                    elif sample_by_prop(attr_dependency_p) \
                        and len(dialogue)>0 and last_template['nodes'][-1]['type'] in node_type_to_attribute \
                        and last_dependencies['attribute'] == 'none': 
                        template = copy.deepcopy(last_template)
                        fn, idx = last_turn['template_filename'], last_turn['question_family_index']
                        find_all_unique_objects(dialogue, template, scene_struct, used_objects)
                        unk_attr = sample_unknown_attr(dialogue, template, turn_dependencies)
                        if unk_attr is not None:
                            template = create_query_template(template, turn_dependencies, used_periods)
                            states, outputs = transfer_object(
                                scene_struct, template, metadata,
                                synonyms, turn_dependencies, last_state
                                )
                            ts, qs, ans, tps, eops, lops = outputs
                        else:
                            ts = [] 
                    
                    # Spatial dependency e.g. how about its left? what about in front of it?  
                    elif sample_by_prop(spatial_dependency_p) \
                        and len(dialogue)>0 \
                        and last_template['nodes'][-1]['type'] in ['relate_action_filter_count', 'relate_action_filter_exist'] \
                        and last_dependencies['spatial'] == 'none':
                        template = copy.deepcopy(last_template)
                        fn, idx = last_turn['template_filename'], last_turn['question_family_index']
                        find_all_unique_objects(dialogue, template, scene_struct, used_objects)
                        unk_spatial = sample_unknown_spatial(dialogue, turn_dependencies)
                        template, period_idx = create_relate_template(template, turn_dependencies, used_periods, scene_struct, synonyms)
                        states, outputs = transfer_relate(
                                scene_struct, template, metadata,
                                synonyms, period_idx, turn_dependencies, last_state
                                )
                        ts, qs, ans, tps, eops, lops = outputs
                        assert eops == [[]] and lops == [[]] and tps == [[]]
                        tps = [copy.deepcopy(last_temporal_program)]
                        eops = [copy.deepcopy(last_earlier_obj_program)]
                        lops = [copy.deepcopy(last_unique_obj_program)]
                        
                    else:
                        template = copy.deepcopy(template_original) 
                        fn, idx = key 
                        # avoid using the same template in each dialogue 
                        if (fn,idx) in used_templates: continue
                        # avoid using question template that is not temporally dependent 
                        if sample_by_prop(not_frameqa_p) and template['interval_type'] == 'none': continue 
                        if args.verbose: print('trying template ', fn, idx)
                        if args.time_dfs and args.verbose: tic = time.time()                        
                        template['cutoff'] = cutoff
                        find_all_unique_objects(dialogue, template, scene_struct, used_objects)
                        precompute_unique_dialogue_object_identifiers(template)
                        sample_prior_unique_object(dialogue, template, cutoff) 
                        sample_earlier_unique_object(dialogue, template) 
                        period_idx = sample_period(dialogue, template, scene_struct, 
                                                   turn_dependencies, metadata, used_periods)
                        if period_idx == -1 and template['interval_type']!='none':
                            ts = []
                        # TODO: recheck this part 
                        #elif turn_dependencies['temporal'] == 'during' and \
                        #    'zero_hop' in fn and idx in [18,19] and \
                        #    'zero_hop' in dialogue[-1]['template_filename'] and \
                        #    dialogue[-1]['question_family_index'] in [18,19]:
                        #    ts = [] 
                        else:
                            states, outputs = instantiate_templates_dfs(
                                scene_struct, template, metadata,
                                template_answer_counts[(fn, idx)],
                                synonyms, period_idx, turn_dependencies,
                                max_instances=args.instances_per_template, 
                                turn_pos=len(dialogue)+1,
                                verbose=False)
                            ts, qs, ans, tps, eops, lops = outputs

                    if len(ts) > 0:
                        image_index = int(os.path.splitext(scene_fn)[0].split('_')[-1])
                        for st, t, q, a, tp, eop, lop in zip(states, ts, qs, ans, tps, eops, lops):
                            dialogue.append({
                                'split':split, 'cater_split':cater_split,
                                'image_filename':scene_fn,'image_index':image_index,'image':os.path.splitext(scene_fn)[0],
                                'question':t,'program':q,'answer':a,'state': st, 
                                'temporal_program': tp, 'earlier_object_program': eop, 'last_object_program': lop,
                                'template_filename':fn,'question_family_index':idx,'question_index':len(dialogue),
                                'template': template,
                                'turn_dependencies': turn_dependencies
                            })
                        if args.verbose: print('got one!')
                        num_instantiated += 1
                        template_counts[(fn, idx)] += 1
                        # update to the latest value
                        used_objects = copy.deepcopy(template['used_objects'])
                        used_periods = copy.deepcopy(template['used_periods'])
                        used_templates.add((fn, idx))
                        #print_pretty(num_instantiated, dialogue[-1], scene_struct)
                        #if len(dialogue)>1 and 'one_hop' in dialogue[-2]['template_filename'] and dialogue[-2]['question_family_index']>1:
                            #if 'among' in dialogue[-1]['question']: 
                            #print(dialogue[-2]['question'])
                            #print(dialogue[-2]['answer'])
                            #print(dialogue[-1]['template']['used_periods'][-1])
                            #print(dialogue[-1]['template']['used_objects'])
                            #pdb.set_trace()
                    else:
                        if args.verbose: print('did not get any =(')
                        # reverse back to previous values
                        used_objects = copy.deepcopy(prior_used_objects)
                        used_periods = copy.deepcopy(prior_used_periods)
                        used_templates = copy.deepcopy(prior_used_templates)
                        cutoff = copy.deepcopy(prior_cutoff)
                        if len(dialogue)>0:
                            if used_objects!=dialogue[-1]['template']['used_objects']:
                                pdb.set_trace()
                            if used_periods!=dialogue[-1]['template']['used_periods']:
                                pdb.set_trace()   
                        
                # Heuristic to check the quality of the dialogue
                valid_dial = is_valid_dialogue(dialogue, scene_struct)
                if valid_dial:
                    break
            if not valid_dial:
                continue 

            clean_program(merge_all_programs(dialogue))
            add_other_annotations(dialogue, scene)
            dialogues.append(dialogue)
            #display_plain_dialogue(dialogue, scene_struct)
            #pdb.set_trace()
            
            if len(dialogues)>0:
                break
            
        if len(dialogues)==0:
            no_output_count += 1 
            print('NO DIAL found for {}!'.format(scene_fn))
            continue      
            
        if not os.path.exists(args.output_questions_file):
            os.makedirs(args.output_questions_file)
        output_file = args.output_questions_file + '/' + os.path.splitext(scene_fn)[0] + '.json'
        print('Writing output to %s' % output_file)
        json.dump(dialogues, open(output_file, 'w'))
    
    print(turn_dependency_count)
    print("# with no output: {}".format(no_output_count))
        
if __name__ == '__main__':
    args = parser.parse_args()
    if args.profile:
        import cProfile
        cProfile.run('main(args)')
    else:
        main(args)
