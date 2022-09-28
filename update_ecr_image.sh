#!/bin/bash
account=$1
region=$2
stack_name=$3
name=$4
local_image=$5

REPOSITORY=$account.dkr.ecr.$region.amazonaws.com/$stack_name
IMAGE=$REPOSITORY:$name
AWS_REGION=$region

# docker login
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $IMAGE
Status=$?
if [ $Status -gt 0 ]; then
   echo "ecr login failed"
   exit 1;
fi

# docker tag
docker image tag $local_image $IMAGE
Status=$?
if [ $Status -gt 0 ]; then
   echo "docker image tag failed"
   exit 1;
fi

# docker push
docker push $IMAGE
Status=$?
if [ $Status -gt 0 ]; then
   echo "image push failed for $IMAGE"
   exit 1;
fi

exit 0;
