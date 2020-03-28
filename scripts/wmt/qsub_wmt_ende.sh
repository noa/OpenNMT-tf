#!/bin/bash

set -e
set -u
set -f

NUM_PROC=12
MEM_FREE=16G
HOURS=72

if [ $# -lt 4 ]; then
    echo "Usage: ${0} <DIR> <CONFIG> <GPU> <SEED>"
    exit
fi

JOB_DIR=${ONMT_EXPT_DIR}/${1}
CONFIG=${2}
NUM_GPU=${3}
SEED=${4}

JOB_SCRIPT=${JOB_DIR}/job.sh

cat >${JOB_SCRIPT} <<EOL
#$ -cwd
#$ -V
#$ -w e
#$ -l h_rt=${HOURS}:00:00,num_proc=${NUM_PROC},mem_free=${MEM_FREE}
#$ -N ${1}
#$ -m bea
#$ -j y
#$ -o ${JOB_DIR}/out
#$ -e ${JOB_DIR}/err

# Stop on error
set -e
set -u
set -f

module load cuda10.1/toolkit
module load cuda10.1/blas
module load cudnn/7.6.3_cuda10.1
module load nccl/2.4.7_cuda10.1

onmt-main --model_type Transformer \
	  --data_dir ${ONMT_DATA_DIR} \
	  --run_dir ${JOB_DIR} \
	  --intra_op_parallelism_threads ${NUM_PROC} \
	  --inter_op_parallelism_threads ${NUM_PROC} \
	  --seed ${SEED} \
          --config ${CONFIG} --auto_config \
          train --with_eval --num_gpus ${NUM_GPU} \

EOL

echo "$JOB_SCRIPT"
chmod a+x ${JOB_SCRIPT}
qsub -q gpu.q@@2080 -l gpu=${NUM_GPU} ${JOB_SCRIPT}

# eof
