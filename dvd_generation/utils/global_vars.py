"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

# action-based variables 
action_map = {'_slide': 'sliding', '_rotate': 'rotating', '_pick_place': 'flying', 
                 '_contain': 'flying'}
action_to_verb_map = {'sliding': 'slide', 'rotating': 'rotate', 'flying': 'fly', 
                 'spinning': 'spin', 'moving': 'move'} #, 'contained': 'is contained'}
action_to_verb_singular_map = {'sliding': 'slides', 'rotating': 'rotates', 'flying': 'flies', 
                 'spinning': 'spins', 'moving': 'moves', 'contained': 'is contained'}
action_to_noun_map = {'sliding': 'slide', 'rotating': 'rotation', 'flying': 'flight', 
                 'spinning': 'spin', 'moving': 'move'} #, 'contained': 'time being contained'}

# ordinal and frequency variables 
ordinal_map={1:'first',2:'second',3:'third',4:'fourth',5:'fifth',
                6:'sixth',7:'seventh',8:'eighth',9:'ninth',10:'tenth'}
reverse_ordinal_map = {v:k for k,v in ordinal_map.items()}
frequency_to_number={"once":1, "twice":2, "three times":3, "four times":4}

# thresholds for video segments
interval_threshold = 10
overlap_threshold = 5
cutoff_interval_threshold = 50 

# global vars for object attributes
identifier_attrs = ['<Z>', '<C>', '<M>', '<S>']
identifier_attr_names = ['size', 'color', 'material', 'shape']
attribute_to_text = {k:v for k,v in zip(identifier_attrs,identifier_attr_names)}
node_type_to_attribute = {'query_size': '<Z>', 'query_shape': '<S>', 'query_color': '<C>', 'query_material': '<M>'}
attribute_to_node_type = {v:k for k,v in node_type_to_attribute.items()}

# global vars for spatial and temporal information
relate_attrs = ['left', 'right', 'behind', 'front']
intervals_to_periods = {'atomic': 'periods', 'compositional': 'all_periods'}

# to avoid dead end cases, sampling by probabilities 
video_cutoff_p = 0.7 
attr_dependency_p = 0.7 
spatial_dependency_p = 0.7
not_frameqa_p = 0.8
not_none_temporal_dependency_p = 0.9 
whole_video_p = 0.1
unique_interval_p = 0.9
last_unique_period_p = 0.9
earlier_unique_period_p = 0.9

# to avoid infinite loops, specify the number of attempts
max_period_sampling_attempts = 10000
max_turn_sampling_attempts = 1000
max_dial_sampling_attempts = 100
