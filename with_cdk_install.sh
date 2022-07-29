#!/bin/bash
python3 -m venv .env
source .env/bin/activate
yum -y update
curl -sL https://rpm.nodesource.com/setup_16.x | bash -
yum list available nodejs
yum install -y python3-pip
yum install -y nodejs
npm install --location=global aws-cdk
python3 -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e cyclone-cli/

#cat orchestrator.tar | docker import - orchestrator_baseimage:latest
echo ''
echo '"hyper" CLI installed, use hyper --help to get started'
echo ''
echo 'You will need DOCKER installed and running to create your first host'