"""
Copyright (c) Facebook, Inc. and its affiliates.
All rights reserved.
This source code is licensed under the license found in the
LICENSE file in the root directory of this source tree.
"""

import argparse

parser = argparse.ArgumentParser()

# Inputs
parser.add_argument(
    '--input_scene_file',
    default='../output/CLEVR_scenes.json',
    help="JSON file containing ground-truth scene information for all images "
    + "from render_images.py")
parser.add_argument(
    '--metadata_file',
    default='question_templates/metadata.json',
    help="JSON file containing metadata about functions")
parser.add_argument(
    '--synonyms_json',
    default='question_templates/synonyms.json',
    help="JSON file defining synonyms for parameter values")
parser.add_argument(
    '--cater_label_file',
    default='',
    help=
    'for dividing data based on the original train/val/test splits from CATER')
parser.add_argument(
    '--template_dir',
    default='question_templates',
    help="Directory containing JSON templates for questions")

# Output
parser.add_argument(
    '--output_questions_file',
    default='../output/CLEVR_questions.json',
    help="The output file to write containing generated questions")

# Control which and how many images to process
parser.add_argument(
    '--scene_start_idx',
    default=0,
    type=int,
    help="The image at which to start generating questions; this allows " +
    "question generation to be split across many workers")
parser.add_argument(
    '--scene_end_idx',
    default=10000,
    type=int,
    help="The image at which to start generating questions; this allows " +
    "question generation to be split across many workers")

#parser.add_argument(
#    '--num_scenes',
#    default=0,
#    type=int,
#    help="The number of images for which to generate questions. Setting to 0 "
#    + "generates questions for all scenes in the input file starting from " +
#    "--scene_start_idx")

# Control the number of questions per image; we will attempt to generate
# templates_per_image * instances_per_template questions per image.
parser.add_argument(
    '--templates_per_image',
    default=10,
    type=int,
    help="The number of different templates that should be instantiated " +
    "on each image")
parser.add_argument(
    '--instances_per_template',
    default=1,
    type=int,
    help="The number of times each template should be instantiated on an image"
)
parser.add_argument(
    '--dialogues_per_image',
    default=1,
    type=int,
    help="The number of different dialogues that should be instantiated " +
    "on each image")
parser.add_argument(
    '--turns_per_dialogue',
    default=10,
    type=int,
    help="The number of dialogue turns should be instantiated in a dialogue"
)
parser.add_argument(
    '--max_turns_per_dialogue',
    default=20,
    type=int,
    help="Maximum number of dialogue turns per dialogue"
)

# Control the complexity of question being generated
parser.add_argument(
    '--above_below_relate',
    action='store_true',
    help='If given the consider above and below spatial relationship')

# Misc
parser.add_argument(
    '--reset_counts_every',
    default=250,
    type=int,
    help="How often to reset template and answer counts. Higher values will " +
    "result in flatter distributions over templates and answers, but " +
    "will result in longer runtimes.")
parser.add_argument(
    '--verbose', action='store_true', help="Print more verbose output")
parser.add_argument(
    '--time_dfs',
    action='store_true',
    help="Time each depth-first search; must be given with --verbose")
parser.add_argument(
    '--profile', action='store_true', help="If given then run inside cProfile")

# args = parser.parse_args()
