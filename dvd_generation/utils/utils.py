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
from utils.scene_utils import is_overlap
from simulators.question_engine import answer_earlier_obj_from_all_obj_program, answer_question

def sample_by_prop(p):
    return random.random()>(1-p)

def reset_counts(metadata, templates):
    # Maps a template (filename, index) to the number of questions we have
    # so far using that template
    template_counts = {}
    # Maps a template (filename, index) to a dict mapping the answer to the
    # number of questions so far of that template type with that answer
    template_answer_counts = {}
    node_type_to_dtype = {n['name']: n['output'] for n in metadata['functions']}
    for key, template in templates.items():
        template_counts[key[:2]] = 0
        final_node_type = template['nodes'][-1]['type']
        final_dtype = node_type_to_dtype[final_node_type]
        answers = metadata['types'][final_dtype]
        if final_dtype == 'Bool': answers = [True, False]
        if final_dtype == 'Integer': answers = list(range(0, 11))
        if final_dtype == 'ActionSet': 
            answers = ['no action', 'flying', 'rotating', 'sliding',
                     'flying,rotating', 'rotating,sliding', 'flying,sliding',
                     'flying,rotating,sliding']
        if final_dtype == 'Action':
            answers = copy.deepcopy(answers) 
            answers.remove('static')
            answers.append('no action')
            answers.remove('contained')
 
        template_answer_counts[key[:2]] = {}
        for a in answers:
            template_answer_counts[key[:2]][a] = 0
    return template_counts, template_answer_counts

def sample_question_by_answer_counts(answer_counts, answer, verbose=False):
    # Use our rejection sampling heuristics to decide whether we should
    # keep this template instantiation
    if answer not in answer_counts:
        pdb.set_trace()
    cur_answer_count = answer_counts[answer]
    answer_counts_sorted = sorted(answer_counts.values())
    median_count = answer_counts_sorted[len(answer_counts_sorted) // 2]
    # TODO: Why max with 5??
    median_count = max(median_count, 5)
    if cur_answer_count > 1.1 * answer_counts_sorted[-2]:
        #TODO: Why?
        if verbose: print('skipping due to second count')
        return True
    if cur_answer_count > 5.0 * median_count:
        # TODO: Why?
        if verbose: print('skipping due to median')
        return True 
    return False 

def node_shallow_copy(node):
    new_node = {
        'type': node['type'],
        'inputs': node['inputs'],
    }
    if 'side_inputs' in node:
        new_node['side_inputs'] = node['side_inputs']
    if '_ref_output' in node: 
        new_node['_ref_output'] = node['_ref_output']
    return new_node 

def print_pretty(turn_idx, turn, scene_struct):
    template = turn['template']
    #print("Template: {} template index: {}".format(turn['template_filename'], turn['question_family_index']))
    if turn_idx==1 and len(template['used_objects'])>0: 
        pdb.set_trace()

    used_objs = template['used_objects']
    print("All unique objects:")
    for idx, obj in enumerate(scene_struct['objects']):
    #for k,v in turn['template']['used_objects'].items():
        print("Obj ID: {} GT: {} FOUND: {}".format(
            idx, display_obj(obj), 
            display_obj_attr(used_objs[idx]) if idx in used_objs else ''
        ))
       
    if template['prior_unique_obj']!=-1:
        last_unique_obj = template['prior_unique_obj']
    else:
        last_unique_obj = 'NONE'
    print("The last turn's only unique obj ID: {}".format(last_unique_obj)) 

    if template['earlier_unique_obj']!=-1:
        earlier_unique_obj = template['earlier_unique_obj']
        #template['earlier_unique_obj_attr'] = obj_attr
        #template['earlier_unique_obj_attr_map'] = obj_attr_map
        #template['earlier_unique_obj_node'] = curr_object[1]
    else:
         earlier_unique_obj = 'NONE'
    print("The mentioned earlier unique obj ID: {}".format(earlier_unique_obj)) 
    
    if len(template['ans_objects'])>0: 
        ans_objs = template['ans_objects']
    else:
        ans_objs = 'NONE'
    print("The last turn's output objs ID: {}".format(ans_objs)) 
        
    print("All temporal periods up till now")
    for idx, p in enumerate(template['used_periods']):
        print('Turn# {}: {}'.format(idx+1,p))
    print("Current video cutoff point: {}".format(template['cutoff'])) 
    
    print("Turn depenndencies: {}".format(turn['turn_dependencies']))
    print("Q{}: {} A{}: {}".format(turn_idx, turn['question'], turn_idx, turn['answer']))
    
    for n_idx, n in enumerate(turn['final_all_program']):
        print(n_idx, n) 
    #print(turn['template']['ref_remark'])
    #print()

def display_obj(scene_obj):
    #if obj_idx == -1: return 
    keys = ['size', 'color', 'material', 'shape']
    return ' '.join([scene_obj[k] for k in keys])

def display_obj_attr(obj_attr):
    keys = ['<Z>', '<C>', '<M>', '<S>']
    out = ' '.join([obj_attr[k] for k in keys if k in obj_attr])
    if '<A>' in obj_attr:
        out += ' Act: {}'.format(obj_attr['<A>'])
    return out
        

def display_dialogue(dialogue, scene_struct):
    for turn_idx, t in enumerate(dialogue): 
        print_pretty(turn_idx+1, t, scene_struct)
        pdb.set_trace()

def display_plain_dialogue(dialogue, scene_struct):
    for m,n in enumerate(dialogue):
        print(m+1, n['question'], n['answer'])
        #print_pretty(m+1, n, scene_struct)
        #pdb.set_trace()
        
def merge_sampled_obj_temporal_program(sampled_obj_program, temporal_program):
    assert temporal_program[0]['type'] == 'refer_object'
    sampled_obj_program_len = len(sampled_obj_program)
    for node in temporal_program[1:]:
        node['inputs'] = [i+sampled_obj_program_len-1 for i in node['inputs']]
        sampled_obj_program.append(node)
    return sampled_obj_program

def print_program(p):
    for n_idx, n in enumerate(p):
        print(n_idx, n)
    print()

def update_node_inputs(old_inputs, first_new_input_idx, len_new_inputs):
    new_inputs = []
    for i in old_inputs:
        if i < first_new_input_idx: 
            new_inputs.append(i)
        else:
            new_inputs.append(i+len_new_inputs-1)
    return new_inputs 

def add_obj_nodes(turn, past_turns, program, original_obj_nodes, node_type='earlier_obj_ref'):
    obj_nodes = copy.deepcopy(original_obj_nodes)
    nb_nodes = len(obj_nodes)
    if nb_nodes==0:
        return program
    
    eo_nodes = [n['type'] for n in program if n['type']==node_type]
    if len(eo_nodes)!=1: 
        if len(eo_nodes)==0 and turn['turn_dependencies']['spatial']!='none' and node_type=='earlier_obj_ref':
            return program 
        pdb.set_trace()
    eo_program = []

    found_eo = False 
    for node_idx, node in enumerate(program): 
        if node['type']!=node_type:
            if found_eo:
                node['inputs'] = update_node_inputs(node['inputs'], first_eo_node_idx, nb_nodes)
            eo_program.append(node)
        else:
            found_eo = True 
            for eo_node_idx, eo_node in enumerate(obj_nodes):
                if eo_node_idx == 0: 
                    first_eo_node_idx = node_idx 
                if eo_node['type'] in ['track_object', 'refer_object']:
                    eo_node['inputs'] = [node_idx-1]
                else:
                    eo_node['inputs'] = [node_idx-1+eo_node_idx for i in eo_node['inputs']]
                eo_program.append(eo_node)
    return eo_program
    
def merge_all_programs(dialogue):
    for turn_idx, turn in enumerate(dialogue): 
        original_p, tp, eop, lop = turn['program'], turn['temporal_program'], \
            turn['earlier_object_program'], turn['last_object_program']
        p = copy.deepcopy(original_p)
        #old_tp = copy.deepcopy(tp)
        #old_eop = copy.deepcopy(eop)
        #old_p = copy.deepcopy(p)
        #old_lop = copy.deepcopy(lop)
        len_tp = len(tp)
        len_eop = len(eop)
        len_lop = len(lop)
        program = p
        
        tp_link_nodes = ['action_count', 'filter_action', 'filter_actions',
                'same_action_set', 'same_action_seq',
                'query_action', 'query_action_set',
                'query_action_seq', 'query_action_freq', 'query_action_order',
                'relate'
                ]

        if len_tp > 0:
            program = tp 
            for node_idx, node in enumerate(p):
                if node_idx == 0: 
                    assert node['type'] == 'scene'
                    #node['inputs'] = [len_tp-1]
                else:
                    node['inputs'] = [i+len_tp for i in node['inputs']]
                    if node['type'] in tp_link_nodes:
                        node['inputs'].append(len_tp-1)
                program.append(node)
            #for o, n in enumerate(program):
            #    print(o,n)

        program = add_obj_nodes(turn, dialogue[0:turn_idx], program, eop, 'earlier_obj_ref')
        program = add_obj_nodes(turn, dialogue[0:turn_idx], program, lop, 'unique_obj_ref')   
        turn['all_program'] = program    
    return dialogue
          
def remove_identity_nodes(nodes):
    old_nodes = copy.deepcopy(nodes)
    #has_identity = True 
    #flag = False
    two_ranges = True
    while(two_ranges):
        found_identity = False 
        two_ranges = False
        identity_idx = []
        new_nodes = []
        for node_idx, node in enumerate(nodes):
            if node['type'] == 'identity':
                if nodes[node_idx-1]['type']!='identity':
                    if found_identity:
                        two_ranges = True
                        #flag = True
                        new_nodes.append(node)
                        continue 
                identity_idx.append(node_idx)
                found_identity = True
            else:
                if two_ranges:
                    new_nodes.append(node)
                    continue 
                count_identities = len(identity_idx)
                if count_identities>0: 
                    last_identity_node_idx = identity_idx[-1]
                    inputs = nodes[node_idx]['inputs']
                    new_inputs = []
                    for i in inputs:
                        if i > last_identity_node_idx-1:
                            new_inputs.append(i-count_identities)
                        else:
                            new_inputs.append(i)
                    nodes[node_idx]['inputs'] = new_inputs
                new_nodes.append(node)
        nodes = new_nodes

    return new_nodes 

def check_node_types(turn, nodes):
    new_types = {
            'query_action': 'query_action_set',
            'filter_actions': 'filter_action',
            'unique_obj_ref': 'refer_object',
            'action_count': 'count_action',
            'count': 'count_object',
            'query_action_freq': 'action_by_freq',
            'query_action_order': 'action_by_order',
            'relate': 'relate_spatial'
    }
    check_types = ['earlier_obj_ref', 'identity']
    dependencies = turn['turn_dependencies']
    for node in nodes:
        nt = node['type']
        if nt in new_types:
            node['type'] = new_types[nt]
        if nt in check_types:
            pdb.set_trace()

def clean_program(dialogue):
    for turn_idx, turn in enumerate(dialogue):
        program = copy.deepcopy(turn['all_program'])
        program = remove_identity_nodes(program)
        check_node_types(turn, program)
        turn['final_all_program'] = program

def has_contained_obj(turn, scene): 
    containment = scene['contained_events']
    program = turn['final_all_program']
    period = turn['template']['used_periods'][-1] 
    if period is not None: 
        start = 0 if period[0] is None else period[0][-1]
        end = 300 if period[1] is None else period[1][-1]
    else:
        start = 0
        end = 300
    contained_objs = {}
    for node in program: 
        if node['type'] in ['filter_color', 'filter_shape', 'filter_material', 'filter_size',
                'filter_action', 'same_action_set', 'same_action_sequence',
                'relate_spatial']:
            output = node['_output']
            if type(output)!=list:
                pdb.set_trace()
            for obj in output: 
                if obj in containment: 
                    contains = []
                    total_overlaps = 0
                    for contain_period in containment[obj]:
                        c_start, c_end = contain_period
                        overlap = is_overlap(start, end, c_start, c_end, return_overlap=True) 
                        if overlap>0: 
                            contains.append(contain_period)
                            total_overlaps += overlap 
                    if len(contains)>0:
                        contained_objs[obj] = {}
                        contained_objs[obj]['contain_periods' ] = contains 
                        contained_objs[obj]['contain_time'] = total_overlaps 
    turn['contained_objs'] = contained_objs

def is_effective_obj_tracking(turn, scene):
    program = turn['earlier_object_program']
    if len(program)>0:
        new_program = copy.deepcopy(program)[:-1]
        new_program[0]['type'] = 'scene'
        for node in new_program:
            del node['_output']
        answer_earlier_obj_from_all_obj_program(scene, new_program)
        if program[-2]['_output'] != new_program[-1]['_output']:
            turn['effective_obj_tracking'] = True
    else:
        turn['effective_obj_tracking'] = False

def is_effective_temporal_obj_tracking(turn, scene):
    program = turn['temporal_program']
    if len(program)>0:
        has_earlier = False
        for node in program:
            if node['type'] == 'track_object':
                has_earlier = True
                break
        if has_earlier:
            new_program = copy.deepcopy(program)
            assert new_program[0]['type'] == 'track_object'
            new_program[0]['type'] = 'scene'
            unique_node_idx = -1
            for node_idx, node in enumerate(new_program):
                if node['type'] == 'unique':
                    unique_node_idx = node_idx 
                    break
                del node['_output']
            new_program = new_program[:unique_node_idx]
            answer_earlier_obj_from_all_obj_program(scene, new_program)
            if program[unique_node_idx-1]['_output'] != new_program[-1]['_output']:
                turn['effective_temporal_obj_tracking'] = True
            else:
                turn['effective_temporal_obj_tracking'] = False
        else:
            turn['effective_temporal_obj_tracking'] = False
    else:
        turn['effective_temporal_obj_tracking'] = False

def is_effective_interval_tracking(turn, scene):
    interval_type = turn['template']['interval_type']
    turn_dependencies = turn['turn_dependencies']
    if turn_dependencies['temporal'] not in ['during', 'video_update']:
        program = turn['program']
        new_program = copy.deepcopy(program)
        for node in new_program:
            if node['type'] not in ['earlier_obj_ref', 'unique_obj_ref']:
                del node['_output']
        last_turn_period = turn['template']['used_periods'][-2]
        if interval_type == 'compositional':
            all_periods = scene['all_periods']
        else:
            all_periods = scene['periods']
        if last_turn_period not in all_periods:
            turn['effective_interval_tracking'] = True 
        else:
            period_idx = all_periods.index(last_turn_period)
            question = {'nodes': new_program}
            answer_question(question, None, scene, period_idx,
                turn_dependencies, all_outputs=True)
            if '_output' not in question['nodes'][-1]:
                is_invalid = False
                for node in question['nodes']:
                    output = node['_output']
                    if output == '__INVALID__':
                        is_invalid = True 
                        break
                assert is_invalid 
                turn['effective_interval_tracking'] = True
            elif question['nodes'][-1]['_output'] != program[-1]['_output']:
                turn['effective_interval_tracking'] = True
            else:
                turn['effective_interval_tracking'] = False
    else:
        turn['effective_interval_tracking'] = False

def is_effective_temporal_localizing(turn, scene):
    interval_type = turn['template']['interval_type']
    turn_dependencies = turn['turn_dependencies']
    if interval_type == 'compositional':
        program = turn['program']
        new_program = copy.deepcopy(program)
        for node in new_program:
            if node['type'] not in ['earlier_obj_ref', 'unique_obj_ref']:
                del node['_output']
        whole_video_period = (None,turn['template']['cutoff'])
        if turn['template']['used_periods'][-1] == whole_video_period:
             turn['effective_temporal_localizing'] = False
        else:
            period_idx = scene['all_periods'].index(whole_video_period)
            question = {'nodes': new_program}
            answer_question(question, None, scene, period_idx, 
                turn_dependencies, all_outputs=True)
            if question['nodes'][-1]['_output'] != program[-1]['_output']:
                turn['effective_temporal_localizing'] = True
            else:
                turn['effective_temporal_localizing'] = False 
    elif interval_type == 'atomic':
        turn['effective_temporal_localizing'] = True
    else:
        turn['effective_temporal_localizing'] = False 

def add_other_annotations(dialogue, scene):
    for turn_idx, turn in enumerate(dialogue):
        has_contained_obj(turn, scene)
        if turn_idx>0: 
            is_effective_obj_tracking(turn, scene)
            is_effective_temporal_obj_tracking(turn, scene)
            is_effective_interval_tracking(turn, scene)
        is_effective_temporal_localizing(turn, scene)
        
        
    
    
    
    
    
    
