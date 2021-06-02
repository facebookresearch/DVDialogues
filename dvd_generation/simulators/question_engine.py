"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

#import json, os, math
#import pdb
#from collections import defaultdict
#from utils.utils import *
#from utils.scene_utils import get_action_by_moment
import copy 
from functools import partial
from utils.global_vars import *
from simulators.spatial_question_engine import *
from simulators.temporal_question_engine import *

temporal_question_handlers = {
    'filter_action': partial(actions_filter_handler, interval_type='atomic'), 
    'filter_actions': partial(actions_filter_handler, interval_type='compositional'), 
    'relate': relate_handler,
    'action_count': action_count_handler, 
    'query_action': make_query_action_handler('action'), 
    'query_action_set': make_query_action_handler('action_set'),
    'query_action_seq': make_query_action_handler('action_seq'),
    'query_action_order': make_query_action_handler('action_order'),
    'query_action_freq': make_query_action_handler('action_freq'),
    #'same_action': same_action_handler,
    'same_action_set': make_same_actions_handler('set'),
    'same_action_seq': make_same_actions_handler('seq')
}

spatial_question_handlers = {
    'scene': scene_handler,
    'filter_color': make_filter_attr_handler('color'),
    'filter_shape': make_filter_attr_handler('shape'),
    'filter_material': make_filter_attr_handler('material'),
    'filter_size': make_filter_attr_handler('size'),
    'unique': unique_handler,
    'union': union_handler,
    'intersect': intersect_handler,
    'count': count_handler,
    'exist': exist_handler,    
    'query_color': make_query_attr_handler('color'),
    'query_shape': make_query_attr_handler('shape'),
    'query_material': make_query_attr_handler('material'),
    'query_size': make_query_attr_handler('size'),
    'same_color': make_same_attr_handler('color'),
    'same_shape': make_same_attr_handler('shape'),
    'same_size': make_same_attr_handler('size'),
    'same_material': make_same_attr_handler('material'),
    'equal_color': equal_handler,
    'equal_shape': equal_handler,
    'equal_integer': equal_handler,
    'equal_material': equal_handler,
    'equal_size': equal_handler,
    'equal_action': equal_handler,
    'equal_object': equal_handler,
    'less_than': less_than_handler,
    'greater_than': greater_than_handler
}


def answer_question(question,
                    metadata,
                    scene_struct,
                    period_idx, 
                    turn_dependencies, 
                    all_outputs=False,
                    cache_outputs=True):
    """
    Use structured scene information to answer a structured question. Most of the
    heavy lifting is done by the execute handlers defined above.

    We cache node outputs in the node itself; this gives a nontrivial speedup
    when we want to answer many questions that share nodes on the same scene
    (such as during question-generation DFS). This will NOT work if the same
    nodes are executed on different scenes.
    """
    all_input_types, all_output_types = [], []
    node_outputs = []
    for node in question['nodes']:
        if cache_outputs and '_output' in node:
            node_output = node['_output']
        else:
            node_type = node['type']
            node_inputs = [node_outputs[idx] for idx in node['inputs']]
            side_inputs = node.get('side_inputs', [])
            if node_type in spatial_question_handlers:
                handler = spatial_question_handlers[node_type]
                node_output = handler(scene_struct, node_inputs, side_inputs)
            elif node_type in temporal_question_handlers:
                handler = temporal_question_handlers[node_type]
                period_relation = 'excluding' if turn_dependencies['temporal'] == 'excluding' else 'during'
                node_output = handler(scene_struct, node_inputs, side_inputs, period_idx, period_relation)
            elif node_type == 'identity':
                node_output = node_outputs[-1] 
            else:
                pdb.set_trace()
            if cache_outputs:
                node['_output'] = node_output
        node_outputs.append(node_output)
        if node_output == '__INVALID__':
            break

    if all_outputs:
        return node_outputs
    else:
        return node_outputs[-1]


def insert_scene_node(nodes, idx):
    # First make a shallow-ish copy of the input
    new_nodes = []
    for node in nodes:
        new_node = {
            'type': node['type'],
            'inputs': node['inputs'],
        }
        if 'side_inputs' in node:
            new_node['side_inputs'] = node['side_inputs']
        new_nodes.append(new_node)

    # Replace the specified index with a scene node
    new_nodes[idx] = {'type': 'scene', 'inputs': []}

    # Search backwards from the last node to see which nodes are actually used
    output_used = [False] * len(new_nodes)
    idxs_to_check = [len(new_nodes) - 1]
    while idxs_to_check:
        cur_idx = idxs_to_check.pop()
        output_used[cur_idx] = True
        idxs_to_check.extend(new_nodes[cur_idx]['inputs'])

    # Iterate through nodes, keeping only those whose output is used;
    # at the same time build up a mapping from old idxs to new idxs
    old_idx_to_new_idx = {}
    new_nodes_trimmed = []
    for old_idx, node in enumerate(new_nodes):
        if output_used[old_idx]:
            new_idx = len(new_nodes_trimmed)
            new_nodes_trimmed.append(node)
            old_idx_to_new_idx[old_idx] = new_idx

    # Finally go through the list of trimmed nodes and change the inputs
    for node in new_nodes_trimmed:
        new_inputs = []
        for old_idx in node['inputs']:
            new_inputs.append(old_idx_to_new_idx[old_idx])
        node['inputs'] = new_inputs

    return new_nodes_trimmed


def is_degenerate(question, metadata, scene_struct, answer=None, period_idx=-1, 
                  verbose=False):
    """
  A question is degenerate if replacing any of its relate nodes with a scene
  node results in a question with the same answer.
  """
    if answer is None:
        answer = answer_question(question, metadata, scene_struct)

    for idx, node in enumerate(question['nodes']):
        if node['type'] == 'relate':
            new_question = {'nodes': insert_scene_node(question['nodes'], idx)}
            new_answer = answer_question(new_question, metadata, scene_struct, period_idx)
            if verbose:
                print('here is truncated question:')
                for i, n in enumerate(new_question['nodes']):
                    name = n['type']
                    if 'side_inputs' in n:
                        name = '%s[%s]' % (name, n['side_inputs'][0])
                    print(i, name, n['_output'])
                print('new answer is: ', new_answer)

            if new_answer == answer:
                return True

    return False

def answer_scene_obj_program(program, scene_struct):
    node_outputs = []
    for node in program:
        if '_output' in node: 
            node_outputs.append(node['_output'])
            continue 
        node_type = node['type']
        #print(node['inputs'], node_outputs)
        node_inputs = [node_outputs[idx] for idx in node['inputs']]
        side_inputs = node.get('side_inputs', [])
        if node_type in spatial_question_handlers:
            handler = spatial_question_handlers[node_type]
            node_output = handler(scene_struct, node_inputs, side_inputs)
        node_outputs.append(node_output)
        node['_output'] = node_output
        if node_output == '__INVALID__':
            pdb.set_trace()
    return program

def answer_earlier_obj_program(template, program):
    node_outputs = [program[0]['_output']]
    used_objects = {'objects': {}}
    for o, attrs in template['used_objects'].items():
        if o not in used_objects['objects']: used_objects['objects'][o] = {}
        for an, av in attrs.items():
            if an in attribute_to_text:
                an = attribute_to_text[an]
                used_objects['objects'][o][an] = av 
    for node in program[1:]:
        node_type = node['type']
        node_inputs = [node_outputs[idx] for idx in node['inputs']]
        side_inputs = node.get('side_inputs', [])
        if node_type in spatial_question_handlers:
            handler = spatial_question_handlers[node_type]
            node_output = handler(used_objects, node_inputs, side_inputs)
        node_outputs.append(node_output)
        node['_output'] = node_output
        if node_output == '__INVALID__':
            pdb.set_trace()
    return program

def answer_earlier_obj_from_all_obj_program(scene_struct, program):
    node_outputs = []
    for node in program:
        node_type = node['type']
        node_inputs = [node_outputs[idx] for idx in node['inputs']]
        side_inputs = node.get('side_inputs', [])
        if node_type in spatial_question_handlers:
            handler = spatial_question_handlers[node_type]
            node_output = handler(scene_struct, node_inputs, side_inputs)
        else:
            pdb.set_trace()
        node_outputs.append(node_output)
        node['_output'] = node_output 
        if node_output == '__INVALID__':
            pdb.set_trace()

def answer_find_relate_period(period, program, relate, side_inputs, last_idx=-1, first_module='find_interval'):
    inputs = [last_idx] if last_idx!=-1 else []
    program.append({'type': first_module, 'inputs': inputs, 
                           'side_inputs': side_inputs, '_output': period})
    if relate == 'before':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['before'], '_output': (0, period[0])})
    elif relate == 'until':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['until'], '_output': (0, period[1])})
    elif relate == 'after':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['after'], '_output': (period[1], -1)})
    elif relate == 'since':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['since'], '_output': (period[0], -1)})
    elif relate == 'during':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['during'], '_output': period})
    elif relate == 'video_update':
        program.append({'type': 'relate_temporal', 'inputs': [len(program)-1], 
                   'side_inputs': ['update'], '_output': (period[0], -1)})
    else:
        pdb.set_trace()
            
def update_state(outputs, node_idx, params, param_name_to_type, identifier, state, scene_struct, template, period_idx=-1): 
    old_state = copy.deepcopy(state)
    start_node_idx = state['input_map'][node_idx-1]+1
    end_node_idx = state['input_map'][node_idx]
    all_nodes = state['nodes']
    new_nodes = all_nodes[start_node_idx:end_node_idx]
    obj_idx = outputs[end_node_idx]
    last_output = outputs[start_node_idx-1]
    template_node = template['nodes'][state['next_template_node']-1]
    node_count = 0
    for idx, param in enumerate(params): 
        param_type = param_name_to_type[param]
        param_val = identifier[idx]
        # update values for text generator 
        state['vals'][param] = param_val if param_val is not None else ''
        if param_type == 'Shape' and param_val is None: 
            state['vals'][param] = 'thing'
        if param_val is not None:
            # update program annotation in each node 
            if param_type == 'Action':
                if 'actions' in template_node['type']: 
                    new_node_type = 'filter_actions'
                    assert template['interval_type'] == 'compositional'
                else:
                    new_node_type = 'filter_action'
                    assert template['interval_type'] == 'atomic'
            else:
                new_node_type = 'filter_{}'.format(param_type.lower())

            new_nodes[node_count]['type'] = new_node_type
            new_nodes[node_count]['side_inputs'] =  [param_val]
            node_inputs = [last_output]
            # obtain new _output in each node
            if new_node_type in spatial_question_handlers:
                handler = spatial_question_handlers[new_node_type]
                node_output = handler(scene_struct, node_inputs, [param_val])
            elif new_node_type in temporal_question_handlers:
                handler = temporal_question_handlers[new_node_type]
                period_relation = 'during'
                #if new_node_type == 'filter_action':
                #    pdb.set_trace()
                node_output = handler(scene_struct, node_inputs, [param_val], period_idx, period_relation)
            else:
                pdb.set_trace()
            new_nodes[node_count]['_output'] = node_output 
            last_output = node_output 
            node_count += 1 
            if len(node_output)==0: pdb.set_trace()
    if node_output != [obj_idx]: pdb.set_trace()
    for node in new_nodes[node_count:]:
        node['type']='identity'
        if 'side_inputs' in node: del node['side_inputs']
        node['_output']=node_output
    assert len(all_nodes[end_node_idx:])==1
    state['nodes'] = all_nodes[:start_node_idx] + new_nodes + all_nodes[end_node_idx:]
    #pdb.set_trace()
    #for node in all_nodes[end_node_idx:]:
    #    node['inputs'] = [len(state['nodes'])-1]
    #    state['nodes'].append(node) 
    #state['input_map'][node_idx] = len(state['nodes'])-1
