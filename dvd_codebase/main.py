"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

#!/usr/bin/env python
import math
import sys
import time
import os
import json
import numpy as np
import pickle as pkl
import threading
import pdb 
from tqdm import tqdm 
import torch
import torch.nn as nn

from configs.configs import *
import data.data_handler as dh

def run_epoch(loader, epoch):
    it = tqdm(enumerate(loader),total=len(loader), desc="epoch {}/{}".format(epoch+1, args.num_epochs), ncols=0)
    for j, batch in it:  
        batch.move_to_cuda()
        pdb.set_trace()
                        
# load dialogues 
logging.info('Loading dialogues from {}'.format(args.data_dir))
train_dials, train_vids = dh.load_dials(args, 'train')
logging.info('#train dials = {} # train videos = {}'.format(len(train_dials), len(train_vids)))
val_dials, val_vids = dh.load_dials(args, 'val') 
logging.info('#val dials = {} # val videos = {}'.format(len(val_dials), len(val_vids)))

# load video features 
logging.info('Loading video features from {}'.format(args.fea_dir))
train_vft, vft_dims, clip_size, clip_stride, segment_map = dh.load_videos(args, train_vids)
val_vft, _, _, _, _ = dh.load_videos(args, val_vids)
logging.info('#video ft dims = {} clip size {} clip stride {}'.format(vft_dims, clip_size, clip_stride))

# get vocabulary
logging.info('Extracting vocabulary')
vocab, answer_list = dh.get_vocabulary(train_dials, args)
logging.info('#vocab = {} #answer candidates = {}'.
        format(len(vocab), len(answer_list)))
logging.info('All answer candidates: {}'.format(answer_list))
unk_words = dh.get_vocabulary(val_dials, args, vocab=vocab)
logging.info('{} unknown words in val split: {}'.format(len(unk_words), unk_words))

# question-answer distribution 
qa_dist = dh.answer_by_question_type(train_dials)
    
# save meta parameters
path = args.output_dir + '.conf'
with open(path, 'wb') as f:
    pkl.dump((vocab, answer_list, qa_dist, args), f, -1)
path2 = args.output_dir + '_params.txt'
with open(path2, "w") as f: 
    for arg in vars(args):
        f.write("{}={}\n".format(arg, getattr(args, arg)))
        
# load data
logging.info('Creating training instances')
train_dials = dh.create_dials(train_dials, vocab, answer_list, segment_map, train_vft, args)
logging.info('Creating validation instances')
valid_dials = dh.create_dials(val_dials, vocab, answer_list, segment_map, val_vft, args)

# make dataloaders 
train_dataloader, train_samples = dh.create_dataset(train_dials, vocab, 'train', args)
logging.info('#train sample = {} # train batch = {}'.format(train_samples, len(train_dataloader)))
valid_dataloader, valid_samples = dh.create_dataset(valid_dials, vocab, 'val', args)
logging.info('#train sample = {} # train batch = {}'.format(valid_samples, len(valid_dataloader)))

epoch_counts = 0
for epoch in range(args.num_epochs):
    # train on training data 
    logging.info('-------training--------')
    train_losses = run_epoch(train_dataloader, epoch)
    
    # test on validation data 
    logging.info('-------validation--------')
    valid_losses = run_epoch(valid_dataloader, epoch)
            
