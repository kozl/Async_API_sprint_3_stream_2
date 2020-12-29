FROM python:3.8

ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV ELASTIC_HOST=es01
ENV ELASTIC_PORT=9200

COPY src/ /src
RUN pip3 install -U pip && pip3 install -r /src/requirements.txt

CMD python3 /src/main.py