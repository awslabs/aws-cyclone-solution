FROM amazon/aws-lambda-python:3.8

ENV AWS_CDK_VERSION=latest
ENV AWS_DEFAULT_REGION=us-east-1


WORKDIR /opt/stack

COPY requirements.txt /opt/stack
COPY lambda-requirements.txt /opt/stack
COPY app.py /opt/stack
COPY hyper_batch /opt/stack/hyper_batch
COPY orchestrator.py /opt/stack
COPY cdk.json /opt/stack
COPY Dockerfile /opt/stack
COPY 0-worker-agent /opt/stack/0-worker-agent
COPY 1-api-handler-lambda /opt/stack/1-api-handler-lambda
COPY 2-dynamo-stream-lambda /opt/stack/2-dynamo-stream-lambda
COPY 3-kinesis-batch-lambda /opt/stack/3-kinesis-batch-lambda
COPY 4-get-start-delete-lambda /opt/stack/4-get-start-delete-lambda
COPY 5-async-stream-lambda /opt/stack/5-async-stream-lambda
COPY 6-dynamo-to-elasticsearch /opt/stack/6-dynamo-to-elasticsearch
COPY 7-async-to-elasticsearch /opt/stack/7-async-to-elasticsearch
COPY 8-failed-worker-lambda /opt/stack/8-failed-worker-lambda
COPY 9-log-stream-lambda /opt/stack/9-log-stream-lambda
COPY 10-dynamo-to-logs-lambda /opt/stack/10-dynamo-to-logs-lambda
COPY 11-async-to-logs-lambda /opt/stack/11-async-to-logs-lambda
COPY 12-vpc-peering-lambda /opt/stack/12-vpc-peering-lambda
COPY 13-api-config-lambda /opt/stack/13-api-config-lambda

RUN yum -y update && \
    #curl -sL https://rpm.nodesource.com/setup_16.x | bash - && \
    yum install https://rpm.nodesource.com/pub_16.x/nodistro/repo/nodesource-release-nodistro-1.noarch.rpm -y && \
    yum install nodejs -y --setopt=nodesource-nodejs.module_hotfixes=1 && \
   # yum list available nodejs && \
    yum install -y python3-pip && \
    yum install -y nodejs && \
    npm install -g aws-cdk@${AWS_CDK_VERSION} && \
    pip3 install -r requirements.txt

CMD ["orchestrator.py"]
ENTRYPOINT ["python"]