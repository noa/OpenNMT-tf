#!/bin/bash

set -e

DATA_PATH=${ONMT_DATA_DIR}/wmt_ende
SENTENCE_PIECE_MODEL=${ONMT_DATA_DIR}/data
runconfig=wmt_ende_transformer
testset=newstest2017-ende
sl=en
tl=de

#wget -nc https://raw.githubusercontent.com/OpenNMT/OpenNMT-tf/master/third_party/input-from-sgm.perl
#wget -nc https://raw.githubusercontent.com/OpenNMT/OpenNMT-tf/master/third_party/multi-bleu-detok.perl

perl input-from-sgm.perl < ${DATA_PATH}/test/$testset-src.$sl.sgm \
   | spm_encode --model=${SENTENCE_PIECE_MODEL}/wmt$sl$tl.model > data/$testset-src.$sl
perl input-from-sgm.perl < ${DATA_PATH}/test/$testset-ref.$tl.sgm > data/$testset-ref.$tl

if true; then
    onmt-main \
	--data_dir ${ONMT_DATA_DIR} \
	--run_dir ${ONMT_EXPT_DIR} \
        --config config/custom_wmt_ende.yml --auto_config \
        --checkpoint_path=${ONMT_EXPT_DIR}/ckpt_avg \
        infer \
        --features_file data/$testset-src.$sl \
        > data/$testset-src.hyp.$tl
fi

if true; then
  spm_decode --model=data/wmt$sl$tl.model --input_format=piece \
             < data/$testset-src.hyp.$tl \
             > data/$testset-src.hyp.detok.$tl

  perl multi-bleu-detok.perl data/$testset-ref.$tl < data/$testset-src.hyp.detok.$tl
fi
