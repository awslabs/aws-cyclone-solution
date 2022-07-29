#!/bin/bash
## BEGIN HYPER SETTINGS: Note HYPER lines MUST start with #
#HYPER -n example-job-name
#HYPER -q sample-queue-1
#HYPER -r 2
#HYPER -d sample-def-1
## END HYPER SETTINGS
## BEGIN ACTUAL CODE
for i in $(seq 60)
do
    echo $i seconds
    sleep 1
done
## END ACTUAL CODE
