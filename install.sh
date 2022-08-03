#!/bin/bash
#python3 -m venv .env
#source .env/bin/activate
python3 -m pip install --upgrade pip
mkdir .lambda_dependencies/
mkdir .lambda_dependencies/python/
pip3 install -r lambda-requirements.txt -t .lambda_dependencies/python/

pip3 install awscli
pip3 install boto3
pip3 install botocore
pip3 install click==8.0.3
pip3 install jsii
pip3 install jsonpickle==2.0.0
pip3 install aiohttp
pip3 install requests
pip3 install -e cyclone-cli/
pip3 install py-cpuinfo
pip3 install psutil

if ! hyper; then
   echo Attempting to use root
   sudo pip3 install -e cyclone-cli/;
else
   echo ''
   echo '"hyper" CLI installed, use hyper --help to get started'
   echo ''
   echo 'You will need DOCKER installed and running to create your first host'
   exit 0;
fi

if ! hyper; then
   echo Attempting to use root and user home dir
   sudo -H pip3 install -e cyclone-cli/;
else
   echo ''
   echo '"hyper" CLI installed, use hyper --help to get started'
   echo ''
   echo 'You will need DOCKER installed and running to create your first host'
   exit 0;
fi