#!/bin/bash

#  Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#-----------------------------------------------------------------------------------------------
#OPTIONAL USER LOGIC SECTION
#-----------------------------------------------------------------------------------------------
#### YOU CAN ADD YOUR OWN LOGIC HERE THAT YOU WANT TO RUN WHEN A WORKER STARTS
#### KEEP IN MIND THAT A WORKER WILL EXECUTE MULTIPLE JOBS IN SERIES WITH A MATCHING TASK DEFINITION




#-----------------------------------------------------------------------------------------------
### MOUNT EFS FILE SYSTEM
#-----------------------------------------------------------------------------------------------
#### EFS FILE SYSTEM SHOULD BE IN MAIN REGION VPC AND HUB REGIONS NEEDS PEERING WITH MAIN REGION OPTION ENABLED
#### ALTERNATIVLY MAKE SURE ALL REGIONS CAN REACH THE EFS FILE SYSTEM
#### REMOVE THE SINGLE HASHES IN LINES BELOW AND PROVIDE THE IP OF YOUR EFS FILE SYSTEM AND LOCAL DIRECTORY TO USE
#### MAKE SURE THE IMAGE HAS nfs-utils INSTALLED ALREADY OR INSTALL IT HERE BEFORE MOUNTING.

### USER INPUT BELOW
#### ENTER IP OF FILE SYSTEM BELOW AND THE DIRECTORY TO CREATE ON CONTAINER WHERE FILE SYSTEM IS THEN MOUNTED
#### AS WELL AS REMOTE DIRECTORY TO MOUNT ON EFS (DEFAULT BELOW IS ROOT ON FILE SYSTEM)
#efs_ip=10.0.0.1
#local_dir=efs
#remote_dir=/

#### INSTALL nfs-utils IF NOT ALREADY ON IMAGE
#sudo yum -y install nfs-utils

#### CREATE DIRECTORY ON CONTAINER WHERE EFS WILL BE MOUNTED
#mkdir $local_dir

#### MOUNT FILE SYSTEM
#sudo mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport $efs_ip:$remote_dir $local_dir


#-----------------------------------------------------------------------------------------------
#DO NOT CHANGE - This is needed to pull worker agent from s3 and start it
#-----------------------------------------------------------------------------------------------
aws s3 cp $1 /
python batch_processor.py --sf_arn=$2 --async_table=$3 --sqs_job_definition=$4 --region=$5 --main_region=$6 --stack_name=$7
#-----------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------