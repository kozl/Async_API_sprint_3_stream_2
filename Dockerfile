FROM python:3.8
COPY src/ /src
RUN pip install -U pip && pip install -r /src/requirements.txt
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV ELASTIC_HOST=es01
ENV ELASTIC_PORT=9200
CMD python3 /src/main.py