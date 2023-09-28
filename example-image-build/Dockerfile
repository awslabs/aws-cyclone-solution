FROM python

COPY start.sh /

RUN pip install --upgrade pip && \
    pip install boto && \
    pip install boto3 && \
    pip install awscli && \
    pip install psutil && \
    pip install jsonpickle && \
    pip install py-cpuinfo==8.0.0.0

RUN pwd
RUN chmod +x start.sh


CMD ["ls"]