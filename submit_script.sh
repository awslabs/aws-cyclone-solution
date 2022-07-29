#!/bin/bash

tasks_per_thread=10
threads=10
cpu_threshold=8000

function wait_cpu_low() {
  threshold=$cpu_threshold
  while true; do
    current=$(uptime | awk '{ gsub(/,/, ""); print $10 * 100; }')
    if [ $current -lt $threshold ]; then
      break;
    else
      sleep 5
    fi
  done
}


for i in $(seq $threads)
do
    for i in $(seq $tasks_per_thread); do qsub qsub_example_file.sh; done &
    sleep 1
    wait_cpu_low
done

