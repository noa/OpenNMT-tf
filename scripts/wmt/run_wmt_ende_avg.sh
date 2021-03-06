#!/bin/bash

onmt-main --model_type Transformer \
	  --data_dir ${ONMT_DATA_DIR} \
	  --run_dir ${ONMT_EXPT_DIR} \
	  --config config/custom_wmt_ende.yml --auto_config \
	  average_checkpoints \
	  --output_dir ${ONMT_EXPT_DIR}/ckpt_avg \
	  --max_count 5 \
