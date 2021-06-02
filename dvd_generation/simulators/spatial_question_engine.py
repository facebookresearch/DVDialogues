"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import json, os, math
import pdb
from collections import defaultdict
from utils.utils import *

def scene_handler(scene_struct, inputs, side_inputs):
    # Just return all objects in the scene
    return list(range(len(scene_struct['objects'])))
    
def unique_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    if len(inputs[0]) != 1:
        return '__INVALID__'
    return inputs[0][0]

def union_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 2
    assert len(side_inputs) == 0
    return sorted(list(set(inputs[0]) | set(inputs[1])))

def intersect_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 2
    assert len(side_inputs) == 0
    return sorted(list(set(inputs[0]) & set(inputs[1])))

def count_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    return len(inputs[0])
   
def make_same_attr_handler(attribute):
    def same_attr_handler(scene_struct, inputs, side_inputs):
        cache_key = '_same_{}'.format(attribute)
        if cache_key not in scene_struct:
            cache = {}
            for i, obj1 in enumerate(scene_struct['objects']):
                same = []
                for j, obj2 in enumerate(scene_struct['objects']):
                    if i != j and obj1[attribute] == obj2[attribute]:
                        same.append(j)
                cache[i] = same
            scene_struct[cache_key] = cache
        cache = scene_struct[cache_key]
        assert len(inputs) == 1
        assert len(side_inputs) == 0
        return cache[inputs[0]]
    return same_attr_handler

def exist_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 1
    assert len(side_inputs) == 0
    return len(inputs[0]) > 0

def equal_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 2
    assert len(side_inputs) == 0
    return inputs[0] == inputs[1]

def less_than_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 2
    assert len(side_inputs) == 0
    return inputs[0] < inputs[1]

def greater_than_handler(scene_struct, inputs, side_inputs):
    assert len(inputs) == 2
    assert len(side_inputs) == 0
    return inputs[0] > inputs[1]

def make_query_attr_handler(attribute):
    def query_attr_handler(scene_struct, inputs, side_inputs):
        assert len(inputs) == 1
        assert len(side_inputs) == 0
        idx = inputs[0]
        obj = scene_struct['objects'][idx]
        
        assert attribute in obj
        val = obj[attribute]
        if type(val) == list and len(val) != 1:
            return '__INVALID__'
        elif type(val) == list and len(val) == 1:
            return val[0]
        else:
            return val
        
    return query_attr_handler

def make_filter_attr_handler(attribute):
    def filter_attr_handler(scene_struct, inputs, side_inputs):
        assert len(inputs) == 1
        assert len(side_inputs) == 1
        value = side_inputs[0]
        output = []
        for idx in inputs[0]:
            if attribute not in scene_struct['objects'][idx]: continue 
            atr = scene_struct['objects'][idx][attribute]
            if value == atr or value in atr:
                output.append(idx)
        return output

    return filter_attr_handler
