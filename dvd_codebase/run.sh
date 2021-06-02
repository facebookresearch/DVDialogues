"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

#input choices
device=$1
debug=$2                # true: test run with small datasets OR false: run with real datasets 

num_epochs=50
batch_size=32
nb_workers=16

# data setting 
data_dir=/workspace/hungle/cater-dialog/question_generation/output/
fea_dir=/workspace/hungle/data/dvd/video-classification-3d-cnn-pytorch/outputs/resnext_101/

# output folder name
expid=baseline

if [ $debug = 1 ]; then 
    expdir=exps_test/$task/${expid}
    num_epochs=3
    nb_workers=0
    report_interval=10
else
    expdir=exps/$task/${expid}                                          
fi
echo stage: $stage debug? $debug task: $task exp_dir: $expdir

# training phase
mkdir -p $expdir
CUDA_VISIBLE_DEVICES=$device python main.py \
      --debug $debug \
      --fea-dir $fea_dir \
      --data-dir $data_dir \
      --output-dir $expdir/dvd \
      --num-epochs $num_epochs \
      --batch-size $batch_size \
      --num-workers $nb_workers \

