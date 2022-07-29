FROM python

COPY start.sh /

RUN pip install --upgrade pip && \
    pip install boto && \
    pip install boto3 && \
    pip install awscli && \
    pip install psutil && \
    pip install py-cpuinfo

RUN pwd
RUN chmod +x start.sh


CMD ["ls"]