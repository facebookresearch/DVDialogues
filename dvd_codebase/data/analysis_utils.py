"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import glob, json, pdb
from tqdm import tqdm
import pandas as pd
import copy, os

def get_question_type(template, prior_template):
    last_node_type = template['nodes'][-1]['type']
    text = template['text'][0].lower()
    if 'same set of activities' in text: 
        qtype = 'compare action set'
    elif 'same sequence of activities' in text:
        qtype = 'compare action sequence'
    elif 'frequently' in text:
        qtype = 'compare int'
    elif 'how many times' in text:
        qtype = 'action count'
    elif 'how many' in text or 'what number' in text:
        qtype = 'obj count'
    elif 'is there' in text: 
        qtype = 'obj exist'
    elif 'what color' in text or 'what material' in text or 'what shape' in text or 'what size' in text:
        qtype = 'attr query'
    elif 'what type of action' in text or 'what is the' in text or 'what types of action' in text:
        qtype = 'action query'
    else:
        assert 'what about' in text
        qtype = get_question_type(prior_template, None)
    return qtype

def get_question_subtype(template, prior_template):
    last_node_type = template['nodes'][-1]['type']
    text = template['text'][0].lower()
    if 'same set of activities' in text: 
        if 'how many' in text:
            qtype = 'compare action set (count)'
        else:
            qtype = 'compare action set (exist)'
    elif 'same sequence of activities' in text:
        if 'how many' in text:
            qtype = 'compare action seq (count)'
        else:
            qtype = 'compare action seq (exist)'
    elif 'frequently' in text:
        if 'as frequently' in text:
            qtype = 'compare int (equal)'
        elif 'less frequently' in text:
            qtype = 'compare int (less)'
        elif 'more frequently' in text:
            qtype = 'compare int (more)'
    elif 'how many times' in text:
        qtype = 'action count'
    elif 'how many' in text or 'what number' in text:
        qtype = 'obj count'
    elif 'is there' in text: 
        qtype = 'obj exist'
    elif 'what color' in text or 'what about its color' in text: 
        qtype = 'attr query (color)'
    elif 'what material' in text or 'what about its material'in text: 
        qtype = 'attr query (material)'
    elif 'what shape' in text or 'what about its shape' in text: 
        qtype = 'attr query (shape)'
    elif 'what size' in text or 'what about its size' in text: 
        qtype = 'attr query (size)'
    elif 'what type of action' in text or 'what is the' in text or 'what types of action' in text:
        if '<o>' in text:
            qtype = 'action query (by order)'
        elif '<f>' in text:
            qtype = 'ation query (by freq)'
        else:
            qtype = 'action query (all actions)'
    else:
        assert 'what about' in text
        assert 'color' not in text and 'size' not in text and \
                'shape' not in text and 'material' not in text
        qtype = get_question_subtype(prior_template, None)
    return qtype

def get_question_complexity(turn, template_fn):
    template = turn['template']
    interval_type = template['interval_type']
    last_node_type = template['nodes'][-1]['type']
    second_last_node_type = template['nodes'][-2]['type']

    if interval_type == 'none': 
        return 'none'
    elif interval_type == 'atomic': 
        if 'one_hop' in template_fn:
            return 'atomic (spatial)'
        else:
            return 'atomic (non-spatial)'
        #return 'atomic'
    elif interval_type == 'compositional':
        return 'compositional'

def get_accuracies_by_type(all_types, models, all_answers, all_results, output_file):
    types = sorted(set(all_types))
    accuracies = {} 
    for t in types:
        accuracies[t] = []
        for model in models:
            nb_corrects = 0 
            count = 0
            results = all_results[model]
            for a_idx, a in enumerate(all_answers):
                curr_type = all_types[a_idx]
                if curr_type != t: continue
                pred = results[a_idx]
                if str(pred) == str(a):
                    nb_corrects += 1 
                count += 1 
            acc = nb_corrects/count 
            accuracies[t].append(acc)  
    df = copy.deepcopy(accuracies)
    df['model'] = models
    df = pd.DataFrame(data=df, columns=['model'] + list(accuracies.keys()))
    df.to_csv(output_file)
    return types, accuracies, df

def get_transfer_accuracies(all_types, models, all_answers, all_results, output_file, is_video_update=False, is_all=False): 
    accuracies = []
    for model in models:
        results = all_results[model]
        nb_corrects = 0 
        count = 0 
        for a_idx, a in enumerate(all_answers):
            if is_all:
                is_single_turn = True
                for k,v in all_types.items():
                    if v[a_idx] != 'none':
                        is_single_turn = False 
                        break
                if is_single_turn: continue 
            else:
                curr_type = all_types[a_idx]
                if is_video_update:
                    if curr_type != 'video_update': continue
                else:
                    if curr_type != 'yes': continue
            prior_pred_a = results[a_idx-1]
            prior_gt_a = all_answers[a_idx-1]
            if str(prior_pred_a) != str(prior_gt_a): continue  
            pred_a = results[a_idx]
            gt_a = all_answers[a_idx]
            if str(pred_a) == str(gt_a):
                nb_corrects += 1 
            count += 1 
        if count == 0:
            acc = 0
        else:
            #pdb.set_trace()
            acc = nb_corrects/count 
        accuracies.append(acc)
    df = {}
    df['accuracies'] = accuracies
    df['model'] = models
    df = pd.DataFrame(data=df, columns=['model', 'accuracies'])
    df.to_csv(output_file)
    return df 

def get_start_end_time(period):
    start, end = period
    if start is None:
        start = 0
    else:
        start = start[-1]
    if end is None:
        end = 301
    else:
        end = end[-1]
    return start, end 

def get_period_size(period):
    if period is None:
        return 0
    start, end = get_start_end_time(period)
    return end - start

def get_overlap_period(curr_period, last_period, ratio=False):
    if curr_period is None:
        return -1 
    if last_period is None:
        return 0 
    s1, e1 = get_start_end_time(curr_period)
    s2, e2 = get_start_end_time(last_period)
    if s2<e1 and s1<e2:
        if ratio:
            return get_period_ratio_bin((min(e1,e2)-max(s1,s2))/(e2-s2))
        else:
            return (min(e1,e2)-max(s1,s2))
    else:
        return 0 

def get_period_distance(curr_period, last_period, point='start'):
    if curr_period is None:
        return -1 
    if last_period is None: 
        return -1 
    s1, e1 = get_start_end_time(curr_period)
    s2, e2 = get_start_end_time(last_period)
    if point == 'start': 
        return abs(s1-s2)
    elif point == 'end':
        return abs(e1-e2) 

def get_period_ratio_bin(ratio):
    if ratio == 0:
        return 0
    for n in range(0,10):
        if ratio*10>n:
            bin = n
        else:
            break
    return bin 

def get_obj_turn_dist(used_objects, dependencies, template, turn_idx):
    all_dists = [0]
    
    if dependencies['object'] != 'none':
        if dependencies['object'] == 'earlier_unique':
            obj_id = str(template['earlier_unique_obj'])
            if obj_id not in used_objects:
                pdb.set_trace()
            turn_dist = turn_idx - used_objects[obj_id]['original_turn'] + 1
            all_dists.append(turn_dist)
        
    if dependencies['temporal'] != 'none':
        if 'earlier_unique' in dependencies['temporal']:
            obj_id = str(template['temporal_obj_id'])
            if obj_id not in used_objects:
                pdb.set_trace()
            turn_dist = turn_idx - used_objects[obj_id]['original_turn'] + 1
            all_dists.append(turn_dist)
        
    return max(all_dists)

def get_stats(dials):
    videos = set()
    questions = set()
    for dial in dials: 
        for turn in dial:
            question = turn['question']
            video = '{}-{}'.format(turn['split'], turn['image_filename'])
            videos.add(video)
            questions.add(question)
    print('# videos: {}'.format(len(videos)))
    print("# dialogues: {}".format(len(dials)))
    print("# unique questions: {}".format(len(questions)))
    output = {
        '#videos': len(videos),
        '#dialogues': len(dials),
        '#unique questions': len(questions)
    }
    return output 

def find_video_end_range(end_time):
    ranges = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270]
    if end_time is None: 
        return 9
    for idx, r in enumerate(ranges):
        if end_time[-1] > r:
            curr_r = idx 
        else:
            return curr_r
    return 9

def find_video_start_range(start_time):
    ranges = [400, 270, 240, 210, 180, 150, 120, 90, 60, 30]
    if start_time is None: 
        return 0
    for idx, r in enumerate(ranges):
        if start_time[-1] <= r:
            curr_r = 9-idx 
        else:
            return curr_r
    return 0
