ARG BUILD_FROM
FROM ${BUILD_FROM} as BUILD_IMAGE

RUN apt-get update \
  && apt-get install -y python3-pip python3 vim \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /pgesmd
COPY requirements.txt .
COPY pgesmd_self_access pgesmd_self_access
RUN pip3 install -r requirements.txt

COPY SelfAccessServer.py .
COPY request_historical_data.py .
COPY entrypoint.sh .
RUN chmod 755 entrypoint.sh
ENTRYPOINT ["/pgesmd/entrypoint.sh"]

EXPOSE 7999
