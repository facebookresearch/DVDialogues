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
from utils.scene_utils import find_event_ordinal
from utils.dialogue_utils import strip_attr_key
from utils.utils import merge_all_programs, clean_program, merge_sampled_obj_temporal_program
from simulators.question_engine import answer_scene_obj_program, answer_earlier_obj_program, answer_find_relate_period
import nltk

def replace_optionals(s):
    """
  Each substring of s that is surrounded in square brackets is treated as
  optional and is removed with probability 0.5. For example the string

  "A [aa] B [bb]"

  could become any of

  "A aa B bb"
  "A  B bb"
  "A aa B "
  "A  B "

  with probability 1/4.
  """
    pat = re.compile(r'\[([^\[]*)\]')

    while True:
        match = re.search(pat, s)
        if not match:
            break
        i0 = match.start()
        i1 = match.end()
        if random.random() > 0.5:
            s = s[:i0] + match.groups()[0] + s[i1:]
        else:
            s = s[:i0] + s[i1:]
    return s

def other_heuristic(text, param_vals, verbose=False):
    """
  Post-processing heuristic to handle the word "other"
  """
    if ' other ' not in text and ' another ' not in text:
        return text
    target_keys = {
        '<Z>',
        '<C>',
        '<M>',
        '<S>',
        '<Z2>',
        '<C2>',
        '<M2>',
        '<S2>',
    }
    if param_vals.keys() != target_keys:
        return text
    key_pairs = [
        ('<Z>', '<Z2>'),
        ('<C>', '<C2>'),
        ('<M>', '<M2>'),
        ('<S>', '<S2>'),
    ]
    remove_other = False
    for k1, k2 in key_pairs:
        v1 = param_vals.get(k1, None)
        v2 = param_vals.get(k2, None)
        if v1 != '' and v2 != '' and v1 != v2:
            if verbose:
                print('other has got to go! %s = %s but %s = %s' % (k1, v1, k2, v2))
            remove_other = True
            break
    if remove_other:
        if ' other ' in text:
            text = text.replace(' other ', ' ')
        if ' another ' in text:
            text = text.replace(' another ', ' a ')
    return text

def instantiate_temporal_object(scene_struct, template, sample_identifier, obj_id, 
                                synonyms, last_unique_obj=False, earlier_unique_obj=False):
    if last_unique_obj:
        temporal_obj_program = []
        temporal_obj_program.append({'type': 'refer_object', 'inputs': [], 
                           'side_inputs': ['its'], '_output': obj_id})
        return temporal_obj_program, 'its'       
    #sample_identifier = template['temporal_obj_attr']
    out = ['the']
    if earlier_unique_obj:
        out += [random.choice(synonyms['<earlier>'])]
    temporal_obj_program = []
    if earlier_unique_obj:
        temporal_obj_program.append({'type': 'track_object', 'inputs': [], 
                                    '_output': list(template['used_objects'].keys())})
    else:
        temporal_obj_program.append({'type': 'scene', 'inputs': []})
    for k in identifier_attrs:
        v = sample_identifier.get(k,None)
        if v!= None: 
            node_type = 'filter_{}'.format(attribute_to_text[k])
            program_node = {'type': node_type, 'inputs': [len(temporal_obj_program)-1], 'side_inputs': [v]}
            temporal_obj_program.append(program_node)
            if v in synonyms:
                v = random.choice(synonyms[v])
                out.append(v)
            else:
                out.append(v) 
        elif k=='<S>':
            out.append('thing')
    if ' '.join(out).replace(' ', '') =='thing': pdb.set_trace()
    temporal_obj_program.append({'type': 'unique', 'inputs': [len(temporal_obj_program)-1]})
    if not earlier_unique_obj:
        program = answer_scene_obj_program(temporal_obj_program, scene_struct)
    else:
        program = answer_earlier_obj_program(template, temporal_obj_program)
    if program[-1]['_output'] != obj_id:
        pdb.set_trace()
    return program, ' '.join(out) 

def instantiate_action(synonyms, event, scene, cutoff):
    out = event[1].split('_')
    action = random.choice(synonyms[out[1]])
    out = action_to_noun_map[out[1]]
    ordinal, period = find_event_ordinal(event, scene, cutoff)
    if ordinal == 'only':
        out = out 
    elif ordinal == 'last':
        out = 'last' + ' ' + out 
    else:
        out = ordinal_map[event[2]] + ' ' + out
    return out, period

def is_sample_action(e1, e2):
    e1 = ' '.join([str(i) for i in e1[:3]]).replace('start_', '')
    e2 = ' '.join([str(i) for i in e2[:3]]).replace('end_', '')
    return e1==e2 

def instantiate_periods(scene_struct, period_idx, synonyms, template, last_unique_obj, earlier_unique_obj, excluding): 
    cutoff = template['cutoff']
    e1 = scene_struct[intervals_to_periods[template['interval_type']]][period_idx][0]
    e2 = scene_struct[intervals_to_periods[template['interval_type']]][period_idx][1]
    assert template['used_periods'][-1] == (e1,e2)
    
    if e1 != None: 
        obj_identifier, obj_id = template['temporal_obj_attr'], template['temporal_obj_id'] 
        o1_program, o1 = instantiate_temporal_object(scene_struct, template, obj_identifier, obj_id,
                                                     synonyms, last_unique_obj, earlier_unique_obj)
        a1, a1_period = instantiate_action(synonyms, e1, scene_struct, cutoff)
        obj_text = [o1] + ["'s"] if o1!='its' else [o1]
        if 'start' in e1[1]:
            oa1 = ['from'] + obj_text + [a1]
        else:
            oa1 = ['after'] + obj_text + [a1]
    
    if e2 != cutoff:
        obj_identifier, obj_id = template['temporal_obj_attr'], template['temporal_obj_id']
        o2_program, o2 = instantiate_temporal_object(scene_struct, template, obj_identifier, obj_id,
                                                     synonyms, last_unique_obj, earlier_unique_obj)
        a2, a2_period = instantiate_action(synonyms, e2, scene_struct, cutoff)
        obj_text = [o2] + ["'s"] if o2!='its' else [o2]
        if 'end' in e2[1]:
            oa2 = ['to'] + obj_text + [a2]
        else:
            oa2 = ['before'] + obj_text + [a2] 
    
    if e1 is None and e2 == cutoff:  
        return [], random.choice(synonyms['whole video']) #, None, -1
    if e1 is None:
        side_inputs = [oa2[-1]]
        if 'start' in e2[1]: 
            answer_find_relate_period(a2_period, o2_program, 'before', side_inputs, last_idx=len(o2_program)-1)
        else:
            oa2[0] = 'until the end of'
            answer_find_relate_period(a2_period, o2_program, 'until', side_inputs, last_idx=len(o2_program)-1)
        out = oa2
        program = o2_program
    elif e2 == cutoff: # and cutoff is None: 
        side_inputs = [oa1[-1]]
        if 'end' in e1[1]: 
            answer_find_relate_period(a1_period, o1_program, 'after', side_inputs, last_idx=len(o1_program)-1)
        else:
            oa1[0] = 'since the start of'
            answer_find_relate_period(a1_period, o1_program, 'since', side_inputs, last_idx=len(o1_program)-1)
        out = oa1
        program = o1_program
    elif is_sample_action(e1, e2):
        out = oa1
        out[0] = 'during'
        answer_find_relate_period(a1_period, o1_program, 'during', [out[-1]], last_idx=len(o1_program)-1)
        program = o1_program
    else:
        if e2[0] == e1[0]: 
            original_len = len(o1_program)
            if 'start' in e1[1]:
                oa2 = ['to'] + ['its'] + [a2]
                out = ['inclusively ,'] + oa1 + oa2
                answer_find_relate_period(a1_period, o1_program, 'since', [oa1[-1]], last_idx=len(o1_program)-1)
                answer_find_relate_period(a2_period, o1_program, 'until', [oa2[-1]], last_idx=original_len-1)
                
                o1_program.append({'type': 'union_interval', 'inputs': [len(o1_program)-3, len(o1_program)-1], 
                           '_output': (a1_period[0], a2_period[1])})
            else:
                oa2 = ['before'] + ['its'] + [a2] 
                out = oa1 + ['and'] + oa2
                answer_find_relate_period(a1_period, o1_program, 'after', [oa1[-1]], last_idx=len(o1_program)-1)
                answer_find_relate_period(a2_period, o1_program, 'before', [oa2[-1]], last_idx=original_len-1)
                
                o1_program.append({'type': 'union_interval', 'inputs': [len(o1_program)-3, len(o1_program)-1], 
                           '_output': (a1_period[1], a2_period[0])})
            program = o1_program
        else:
            pdb.set_trace()
            if 'start' in e1[1]:
                out = ['inclusively ,'] + oa1 + oa2
            else:
                out = oa1 + ['and'] + oa2
    
    out = ' '.join(out)
    
    if last_unique_obj:
        if template['sampled_ans_object']!=-1:
            sampled_obj_program = []
            ans_obj_attr = template['sampled_ans_object_attr']
            attr_str = []
            sampled_obj_program.append({'type': 'refer_object', 'inputs': [], 
                                    'side_inputs': ['them'],
                                    '_output': template['prior_ans_object_group']})
            for name, val in ans_obj_attr.items():
                if val not in ['', 'thing']:
                    node_type = 'filter_{}'.format(attribute_to_text[name])
                    program_node = {'type': node_type, 'inputs': [len(sampled_obj_program)-1], 'side_inputs': [val]}
                    sampled_obj_program.append(program_node)
                if val in synonyms: 
                    val = random.choice(synonyms[val])
                attr_str.append(val)
            if '<S>' not in ans_obj_attr:
                attr_str.append('thing')
            modifier_text = 'Among them , there is a {} . '.format(' '.join(attr_str))
            
            sampled_obj_program.append({'type': 'unique', 'inputs': [len(sampled_obj_program)-1]})
            sampled_obj_program = answer_scene_obj_program(sampled_obj_program, scene_struct)
            assert sampled_obj_program[-1]['_output'] == template['sampled_ans_object']
            program = merge_sampled_obj_temporal_program(sampled_obj_program, program)
        else:
            modifier_text = '{} {} , '.format(random.choice(synonyms['<given>']), random.choice(synonyms['<it>']))
        out = modifier_text + out 
        
    return program, out

def instantiate_temporal_localization(text, template, synonyms, scene_struct, period_idx, turn_dependencies):
    period_program = []
    if template['interval_type'] != 'none':
        if 'none' in turn_dependencies['temporal']:
            period_program, period = instantiate_periods(scene_struct, period_idx, synonyms, 
                                         template, 
                                         'last_unique_obj' in turn_dependencies['temporal'],
                                         'earlier_unique_obj' in turn_dependencies['temporal'],
                                         'excluding' in turn_dependencies['temporal']
                                        )

        elif 'among_' in turn_dependencies['temporal']:
            o, a, _, relate = turn_dependencies['temporal'].split('_')
            sampled_a = random.choice(synonyms[a])
            a_noun = action_to_noun_map[sampled_a]
            period = '{} those {}s, {} the {} one'.format(
                random.choice(synonyms['<among>']),
                a_noun,relate, ordinal_map[int(o)])
            start = 0 if template['new_prior_period'][0] is None else template['new_prior_period'][0][-1]
            end = -1 if template['new_prior_period'][1] is None else template['new_prior_period'][1][-1] 
            side_inputs = ["the {} one".format(ordinal_map[int(o)])]
            answer_find_relate_period((start, end), period_program, relate, side_inputs, first_module='refer_interval')
            
        elif 'prior_' in turn_dependencies['temporal']: 
            _, a , relate = turn_dependencies['temporal'].split('_')
            a_noun = action_to_noun_map[a]
            period = '{} this {}'.format(relate, a_noun) 
            start = 0 if template['new_prior_period'][0] is None else template['new_prior_period'][0][-1]
            end = -1 if template['new_prior_period'][1] is None else template['new_prior_period'][1][-1] 
            answer_find_relate_period((start, end), period_program, relate, ['this ' + a_noun], first_module='refer_interval')
            
        else:
            start = 0 if template['used_periods'][-2][0] is None else template['used_periods'][-2][0][-1]
            end = -1 if template['used_periods'][-2][1] is None else template['used_periods'][-2][1][-1]
            period = random.choice(synonyms[turn_dependencies['temporal']])
            #side_inputs = ["last period"]
            #if 'time' not in period: pdb.set_trace()
            #token_idx = period.split().index('time')
            #side_inputs = [' '.join(period.split()[token_idx-1:])]
            side_inputs = []
            answer_find_relate_period((start, end), period_program, turn_dependencies['temporal'], side_inputs, first_module='track_interval')

        if len(period)>0:
            if turn_dependencies['temporal']!='video_update':
                text = period + ' , ' + text  
            else:
                text = period 
    return text, period_program 
    
def instantiate_last_unique_obj_dependency(text, state, template, synonyms, scene_struct, turn_dependencies):
    last_obj_program = []
    if turn_dependencies['object'] == 'last_unique': 
        if template['sampled_ans_object']!=-1:
            ans_obj_attr = template['sampled_ans_object_attr']
            attr_str = []
            last_obj_program.append({'type': 'refer_object', 'inputs': [],
                                    'side_inputs': ['them'], 
                                    '_output': template['prior_ans_object_group']})
            for name, val in ans_obj_attr.items():
                if val not in ['', 'thing']:
                    node_type = 'filter_{}'.format(attribute_to_text[name])
                    program_node = {'type': node_type, 'inputs': [len(last_obj_program)-1], 'side_inputs': [val]}
                    last_obj_program.append(program_node)
                if val in synonyms: 
                    val = random.choice(synonyms[val])
                attr_str.append(val)
            if '<S>' not in ans_obj_attr:
                attr_str.append('thing')
            modifier_text = 'Among them , there is a {} . '.format(' '.join(attr_str))
            
            last_obj_program.append({'type': 'unique', 'inputs': [len(last_obj_program)-1]})
            last_obj_program = answer_scene_obj_program(last_obj_program, scene_struct)
            assert last_obj_program[-1]['_output'] == template['sampled_ans_object']
            
        elif template['interval_type'] != 'none':
            modifier_text = '{} {} {} , '.format(random.choice(synonyms['<link>']),
                                                 random.choice(synonyms['<given>']), 
                                                 random.choice(synonyms['<it>']))
        else:
            modifier_text = '{} '.format(random.choice(synonyms['<link>']))
        text = modifier_text + text 

        if template['interval_type'] != 'none':
            replace_text = 'it'
        else:
            replace_text = random.choice(synonyms['<it>'])
        unique_text = ' '.join(template['unique_obj'][1]['side_inputs'])
        text = text.replace('the ' + unique_text, replace_text)
        text = text.replace('The ' + unique_text, replace_text)
        # update program parameters with reference phrase
        for n_idx, n in enumerate(state['nodes']):
            if n['type'] == 'unique_obj_ref':
                n['side_inputs'] = [replace_text]
                unique_obj_n_idx = n_idx 
                break
        '''
        # among objects  
        if template['sampled_ans_object']!=-1:
            prior_obj_group = template['prior_ans_object_group']
            new_nodes = []
            new_nodes.append({'type': 'earlier_obj_ref', 'inputs': [unique_obj_n_idx-1], 
                        '_output': prior_obj_group, 'side_inputs': ['them']})
            for atrr in identifier_attrs:
                if attr in template['sampled_ans_object_attr']:
                    param_val = template['sampled_ans_object_attr'][attr]
                    node_type = attribute_to_node_type[attr]
                    pdb.set_trace()
        '''
    return text, last_obj_program 
        
def instantiate_attributes(text, state, template, synonyms, scene_struct, turn_dependencies):
    earlier_obj_program = []
    if turn_dependencies['object'] == 'earlier_unique':
        earlier_obj_program.append({'type': 'track_object', 'inputs': [], 
                                    '_output': list(template['used_objects'].keys())})
    for name, val in state['vals'].items():
        #if val == 'inside' or val == 'covered by': 
        #    pdb.set_trace
        if val is None: pdb.set_trace()
        if name not in text: continue 
        original_val = val
        if val in synonyms: val = random.choice(synonyms[val])
        #if '<A' in name: pdb.set_trace()
        if '<A' in name and 'action_remark' in template:
            if name not in template['action_remark']: pdb.set_trace()
            rm = template['action_remark'][name]
            if rm == 'action_verb':
                if val == '': 
                    pdb.set_trace()
                else:
                    val = action_to_verb_map[val]
            if rm == 'action_verb_singular': 
                if val == '':
                    pdb.set_trace()
                    text = text.replace('that {} at least once'.format(name),'') 
                else:
                    val = action_to_verb_singular_map[val]
        elif '<A' in name and 'remark' in template:
            pdb.set_trace()
        
        # earlier object references 
        if turn_dependencies['object'] == 'earlier_unique':
            if name == template['earlier_unique_obj_node']['side_inputs'][0]:
                #ref_phrase = []
                val = random.choice(synonyms['<earlier>']) + ' ' + val
            if name in template['earlier_unique_obj_node']['side_inputs']:
                #ref_phrase.append(val) 
                if original_val not in ['', 'thing']:
                    node_type = 'filter_{}'.format(attribute_to_text[strip_attr_key(name)])
                    program_node = {'type': node_type, 'inputs': [len(earlier_obj_program)-1], 'side_inputs': [original_val]}
                    earlier_obj_program.append(program_node)
        
        text = text.replace(name, val)             
        text = ' '.join(text.split())
    
    # update program parameters with reference phrase 
    if turn_dependencies['object'] == 'earlier_unique':
        earlier_obj_program.append({'type': 'unique', 'inputs': [len(earlier_obj_program)-1]})
        #ref_phrase = ' '.join(' '.join(ref_phrase).split())
        earlier_obj_program = answer_earlier_obj_program(template, earlier_obj_program)
        assert earlier_obj_program[-1]['_output'] == template['earlier_unique_obj']
        #for n in state['nodes']:
        #    if n['type'] == 'earlier_obj_ref':
        #        n['side_inputs'] = [ref_phrase]
        #        break
        
    return text, earlier_obj_program 

def instantiate_questions(final_states, template, synonyms, scene_struct, period_idx, turn_dependencies=None):
    # Actually instantiate the template with the solutions we've found
    text_questions, structured_questions, answers = [], [], []
    temporal_programs, earlier_obj_programs, last_obj_programs  = [], [], []
    for state in final_states:
        text = random.choice(template['text'])
        temporal_program, earlier_obj_program, last_obj_program = [], [], []
        if turn_dependencies['spatial'] == 'none' and turn_dependencies['attribute'] == 'none':
            text, temporal_program = instantiate_temporal_localization(text, template, 
                                                                     synonyms, scene_struct, period_idx, turn_dependencies)
            text, last_obj_program = instantiate_last_unique_obj_dependency(text, state, template, 
                                                                            synonyms, scene_struct, turn_dependencies)        
            text, earlier_obj_program = instantiate_attributes(text, state, template, synonyms, 
                                                               scene_struct, turn_dependencies)
            text = replace_optionals(text)
        text = ' '.join(nltk.word_tokenize(text))
        text = other_heuristic(text, state['vals']) 
        text = text.lower()
        text_questions.append(text)
        #complete_program = clean_program(merge_program(temporal_program, state['nodes']))
        temporal_programs.append(temporal_program)
        earlier_obj_programs.append(earlier_obj_program)
        last_obj_programs.append(last_obj_program)
        structured_questions.append(state['nodes'])
        answers.append(state['answer'])  
        if len(temporal_program)>10:
            pdb.set_trace()
        if '<z> <c> <m> <s>' in text: 
            pdb.set_trace()
        if 'there is a' in text and template['sampled_ans_object']==-1: 
            pdb.set_trace()
           
    return text_questions, structured_questions, answers, temporal_programs, earlier_obj_programs, last_obj_programs
