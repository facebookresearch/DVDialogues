"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

cater_split=$1 #max2action or all_actions
start_idx=$2
end_idx=$3
out_dir=$4 #output/temp #output/max2action_dial_test
split=$5  #val, train_subsetT, train_subsetV

turns=10
reset_count=100
project_dir=/workspace/hungle/ #/data/users/hle2020/hle_fall_internship_2020
cater_dir=data/dvd/cater/$cater_split
scene_file=$project_dir/$cater_dir/preprocessed_scenes/

if [ "$cater_split" = "max2action" ]; then
    cater_label_file=$project_dir/$cater_dir/lists/actions_present/$split.txt
else
    cater_label_file=$project_dir/$cater_dir/lists/localize/$split.txt
fi
    
python generate_dialogues.py --input_scene_file $scene_file \
    --cater_label_file $cater_label_file \
    --output_questions_file $out_dir \
    --dialogues_per_image 10 --turns_per_dialogue $turns \
    --scene_start_idx $start_idx --scene_end_idx $end_idx \
    --reset_counts_every  $reset_count #--verbose 
    
#python move_to_share.py
