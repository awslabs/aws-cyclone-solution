
#!/bin/bash
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo STOP ALL STATE MACHINES
python ./scripts/stop_all_stepfunctions.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo TERMINATE RUNNING BATCH JOBS AND CANCEL THE REST
python ./scripts/clear_all_batch_jobs.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo TERMINATE RUNNING INSTANCES
python ./scripts/clear_all_ec2_instances.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo CLEAN ASYNC TABLES ACROSS REGIONS
python ./scripts/async_table_clean.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo WAITING 60 SECONDS
sleep 60
echo CLEARING AGAIN
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo STOP ALL STATE MACHINES
python ./scripts/stop_all_stepfunctions.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo TERMINATE RUNNING BATCH JOBS AND CANCEL THE REST
python ./scripts/clear_all_batch_jobs.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo TERMINATE RUNNING INSTANCES
python ./scripts/clear_all_ec2_instances.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py
echo CLEAN ASYNC TABLES ACROSS REGIONS
python ./scripts/async_table_clean.py
echo CLEAR SQS QUEUES
python ./scripts/clear_sqs.py