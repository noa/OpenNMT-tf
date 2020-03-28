#!/bin/bash

NUM_GPU=4
CONFIG=`realpath config/transformer_wmt_ende.yml`
echo "Using config: ${CONFIG}"

[ ! -f ${CONFIG} ] && echo "File not found!"

for i in {1..5}; do
    qsub_wmt_ende.sh ens_ls_${i} ${CONFIG} ${NUM_GPU} ${i}
done

# eof
