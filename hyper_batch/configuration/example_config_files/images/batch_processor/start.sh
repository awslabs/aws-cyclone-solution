#!/bin/bash
aws s3 cp $1 /
python batch_processor.py --sf_arn=$2 --async_table=$3 --sqs_job_definition=$4 --region=$5 --main_region=$6 --stack_name=$7
