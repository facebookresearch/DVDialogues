"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import copy
import logging
import sys
import time
import os
import six
import pickle
import json
import numpy as np
import pdb 
from tqdm import tqdm
import torch 
import nltk


def subsequent_mask(size):
    "Mask out subsequent positions."
    attn_shape = (1, size, size)
    subsequent_mask = np.triu(np.ones(attn_shape), k=1).astype('uint8')
    return torch.from_numpy(subsequent_mask) == 0

def get_npy_shape(filename):
    with open(filename, 'rb') as f:
        if filename.endswith('.pkl'):
            shape = pickle.load(f).shape
        else:
            pdb.set_trace()
            major, minor = np.lib.format.read_magic(f)
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(f)
    return shape

def words2ids(str_in, vocab):
    words =  nltk.word_tokenize(str_in)
    sentence = np.ndarray(len(words)+2, dtype=np.int32)
    sentence[0]=vocab['<sos>']
    for i,w in enumerate(words):
        if w in vocab:
            sentence[i+1] = vocab[w]
        else:
            sentence[i+1] = vocab['<unk>']
    sentence[-1]=vocab['<eos>']
    return sentence

def program2ids(program, vocab):
    sentence = []
    return np.asarray(sentence, dtype=np.int32)
    for n in program: 
        t = n['type']
        if t == 'identity': continue 
        if t not in vocab: 
            print(t)
            pdb.set_trace()
            #else:
            #    t = new_nodes[t]
        sentence.append(vocab[t])
        if 'side_inputs' in n:
            if len(n['side_inputs'])!=1: 
                assert type(n['side_inputs']) == str
                words = n['side_inputs']
            else:
                words = n['side_inputs'][0]
            words = nltk.word_tokenize(words)
            for word in words:
                if word in vocab:
                    sentence.append(vocab[word]) 
                else:
                    sentence.append(vocab['<unk>'])
    #if len(sentence)==0:
    #    pdb.set_trace()
    #    sentence=np.asarray([vocab['<eop>']])
    return np.asarray(sentence, dtype=np.int32)

def state2ids_dot(state, dot_vocab, max_dot_size=10):
    ordered_attrs = ['<Z>', '<C>', '<M>', '<S>']
    ids = {}
    for a in ordered_attrs:
        ids[a] = []
        for o in range(max_dot_size):
            ids[a].append(dot_vocab[a]['<blank>'])
    if len(state)==0:
        return ids
    sorted_state = {k: v for k, v in sorted(state.items(), key=lambda item: item[1]['original_turn'])}
    state_idx = 0 
    for k,v in sorted_state.items():
        for a in ordered_attrs: 
            if a in v:
                ids[a][state_idx] = dot_vocab[a][v[a]]
        state_idx += 1 
    ids = {k:np.asarray(v, dtype=np.int32) for k,v in ids.items()}
    return ids 

def state2ids(state, vocab):
    return np.asarray([], dtype=np.int32)
    if len(state)==0:
        return np.asarray([vocab['<eoo>']], dtype=np.int32)
    sentence = []
    ordered_attrs = ['<Z>', '<C>', '<M>', '<S>']
    #print(state)
    sorted_state = {k: v for k, v in sorted(state.items(), key=lambda item: item[1]['original_turn'])}
    
    for k,v in sorted_state.items():
        found_obj = False
        for a in ordered_attrs:
            if a in v:
                sentence.append(vocab[v[a]])
                found_obj = True
        if found_obj: 
            sentence.append(vocab['<eoo>'])
    if len(sentence)==0:
        return np.asarray([vocab['<eoo>']], dtype=np.int32)
    return np.asarray(sentence, dtype=np.int32)
                
def get_vft_size_by_timestamp(time, segment_map, event_type='end', threshold=5):
    if time is None: 
        if event_type == 'end':
            return len(segment_map)-1
        else:
            return 0
        
    if event_type == 'end':
        segment_idx = -1
        for idx in range(len(segment_map)):
            segment_range = segment_map[idx]
            if segment_range[1]>time[-1]:
                segment_idx = idx-1
                break
        if segment_idx == -1:
            segment_idx = 0 
        return segment_idx
        
    else:
        segment_idx = -1
        for idx in range(len(segment_map)):
            segment_range = segment_map[idx]
            if segment_range[0]>=time[-1]:
                segment_idx = idx
                break
        if segment_idx == -1:
            segment_idx = len(segment_map)-1
        return segment_idx


def get_vft_range_by_period(period, segment_map, eov):
    if period is None:
        return (0, eov)
    else:
        start_time, end_time = period
        start_vft = get_vft_size_by_timestamp(start_time, segment_map, 'start')
        end_vft = get_vft_size_by_timestamp(end_time, segment_map, 'end')
        if start_vft > end_vft:
            start_vft, end_vft = end_vft, start_vft
        return (start_vft, end_vft)
    
