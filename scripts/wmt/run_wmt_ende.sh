#!/bin/bash

set -e
set -u
set -x

onmt-main --model_type Transformer \
	  --data_dir ${ONMT_DATA_DIR} \
	  --run_dir ${ONMT_EXPT_DIR}/${1} \
          --config ${2} --auto_config \
          train --with_eval --num_gpus ${3}

# eof
