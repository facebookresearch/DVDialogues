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
import torch.utils.data as Data
from torch.autograd import Variable
from data.data_utils import *

class Dataset(Data.Dataset):
    def __init__(self, data_info):
        self.vid_split = data_info['vid_split']
        self.vid = data_info['vid']
        self.qa_id = data_info['qa_id']
        self.history = data_info['history']
        self.question = data_info['question']
        self.answer = data_info['answer']
        self.turns = data_info['turns']
        self.curr_vft = data_info['curr_vft']
        self.vft_sizes = data_info['vft_sizes']
        self.gt_period = data_info['gt_period']
        self.program = data_info['program']
        self.state = data_info['state']
        
    def __getitem__(self, index):
        item_info = {
            'vid_split': self.vid_split[index],
            'vid':self.vid[index], 
            'qa_id': self.qa_id[index],
            'history': self.history[index],
            'turns': self.turns[index],
            'question': self.question[index],
            'answer': self.answer[index],
            'curr_vft': self.curr_vft[index],
            'vft_sizes': self.vft_sizes[index],
            'gt_period': self.gt_period[index],
            'program': self.program[index],
            'state': self.state[index],
            }
        return item_info
    
    def __len__(self):
        return len(self.vid)
    
class Batch:
    def __init__(self, vft, his, query, his_query, turns,
                 answer, vid_splits, vids, qa_ids, 
                 query_lens, his_lens, his_query_lens, vft_lens, 
                 dial_lens, turn_lens,
                 program, program_lens, state, state_lens,
                 vocab):
        self.vid_splits = vid_splits
        self.vids = vids
        self.qa_ids = qa_ids
        self.size = len(self.vids)
        
        self.query = query
        self.query_lens = query_lens
        self.his = his
        self.his_lens = his_lens
        self.his_query = his_query
        self.his_query_lens = his_query_lens
        self.answer = answer
        self.vft = vft
        self.vft_lens = vft_lens
        self.turns = turns 
        self.dial_lens = dial_lens
        self.turn_lens = turn_lens 
        
        pad = vocab['<blank>']
        self.his_query_mask = (his_query != pad).unsqueeze(-2)
        self.query_mask = (query != pad).unsqueeze(-2)
        self.his_mask  = (his != pad).unsqueeze(-2)
        self.vft_mask = (vft.sum(-1)!=0).unsqueeze(1)
        if len(self.vft.shape)==5:
            self.vft_mask = (vft.sum(-1).sum(-1).sum(-1)!=0).unsqueeze(1)
        else:
            self.vft_mask = (vft.sum(-1)!=0).unsqueeze(1)
        
        self.program = program
        self.program_lens = program_lens
        self.state = state
        self.state_lens = state_lens

    @staticmethod
    def make_std_mask(tgt, pad):
        tgt_mask = (tgt != pad).unsqueeze(-2)
        tgt_mask = tgt_mask & Variable(subsequent_mask(tgt.size(-1)).type_as(tgt_mask.data))
        return tgt_mask    

    def move_to_cuda(self):
        self.query = self.query.to('cuda', non_blocking=True)
        self.his = self.his.to('cuda', non_blocking=True)
        self.his_query = self.his_query.to('cuda', non_blocking=True)
        self.query_mask = self.query_mask.to('cuda', non_blocking=True)
        self.his_mask = self.his_mask.to('cuda', non_blocking=True)
        self.his_query_mask = self.his_query_mask.to('cuda', non_blocking=True)
        self.answer = self.answer.to('cuda', non_blocking=True)
        self.vft = self.vft.to('cuda', non_blocking=True) 
        self.vft_mask = self.vft_mask.to('cuda', non_blocking=True)
        self.turns = self.turns.to('cuda', non_blocking=True)
        self.program = self.program.to('cuda', non_blocking=True)
        self.state = self.state.to('cuda', non_blocking=True)            
    
    def to_cuda(self, tensor):
        return tensor.cuda()
    
def collate_fn(data, vocab):
    def pad_seq(seqs, pad_token, return_lens=False, is_vft=False):
        lengths = [s.shape[0] for s in seqs]
        max_length = max(lengths)
        output = []
        for seq in seqs:
            if is_vft:
                if len(seq.shape)==4: # spatio-temporal feature
                    result = np.ones((max_length, seq.shape[1], seq.shape[2], seq.shape[3]), dtype=seq.dtype)*pad_token
                else:
                    result = np.ones((max_length, seq.shape[-1]), dtype=seq.dtype)*pad_token
            else:
                result = np.ones(max_length, dtype=seq.dtype)*pad_token
            result[:seq.shape[0]] = seq 
            output.append(result)
        if return_lens:
            return lengths, output
        return output 
    
    def pad_2d_seq(seqs, pad_token, return_lens=False, is_vft=False):
        lens1 = [len(s) for s in seqs]
        max_len1 = max(lens1)
        all_seqs = []
        for seq in seqs:
            all_seqs.extend(seq)
        lens2 = [len(s) for s in all_seqs]
        max_len2 = max(lens2)
        output = []
        all_lens = []
        for seq in seqs:
            if is_vft:
                result = np.ones((max_len1, max_len2, seq[0].shape[-1]))*pad_token
            else:
                result = np.ones((max_len1, max_len2))*pad_token
            turn_lens = np.ones(max_len1, dtype=np.int)
            for turn_idx, turn in enumerate(seq):
                result[turn_idx,:turn.shape[0]] = turn
                turn_lens[turn_idx] = turn.shape[0]
            output.append(result)
            all_lens.append(turn_lens)
        all_lens = np.asarray(all_lens)
        if return_lens:
            return lens1, all_lens, output
        return output

    def prepare_data(seqs, is_float=False):
        if is_float:
            return torch.from_numpy(np.asarray(seqs)).float()
        return torch.from_numpy(np.asarray(seqs)).long()
                        
    item_info = {}
    for key in data[0].keys():
        item_info[key] = [d[key] for d in data]   
    pad_token = vocab['<blank>']
    h_lens, h_padded = pad_seq(item_info['history'], pad_token, return_lens=True)
    h_batch = prepare_data(h_padded)
    q_lens, q_padded = pad_seq(item_info['question'], pad_token, return_lens=True)
    q_batch = prepare_data(q_padded)
    
    hq = [np.concatenate([q,h]) for q,h in zip(item_info['history'], item_info['question'])]
    hq_lens, hq_padded = pad_seq(hq, pad_token, return_lens=True)
    hq_batch = prepare_data(hq_padded) 
    
    dial_lens, turn_lens, turns_padded = pad_2d_seq(item_info['turns'], pad_token, return_lens=True)
    turns_batch = prepare_data(turns_padded)
    a_batch = prepare_data(item_info['answer'])
    
    vft_lens, vft_padded = pad_seq(item_info['curr_vft'], 0, return_lens=True, is_vft=True)        
    vft_batch = prepare_data(vft_padded, is_float=True)

    assert vft_lens == item_info['vft_sizes']
    
    p_lens, p_padded = pad_seq(item_info['program'], pad_token, return_lens=True)
    p_batch = prepare_data(p_padded)
    
    s_lens, s_padded = pad_seq(item_info['state'], pad_token, return_lens=True)
    s_batch = prepare_data(s_padded)                  
    
    batch = Batch(vft_batch,  
                  h_batch, q_batch, hq_batch, turns_batch, a_batch, 
                  item_info['vid_split'], item_info['vid'], item_info['qa_id'], 
                  q_lens, h_lens, hq_lens, vft_lens, 
                  dial_lens, turn_lens,
                  p_batch, p_lens, s_batch, s_lens,
                  vocab)
    return batch
