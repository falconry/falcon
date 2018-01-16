FROM python:3.6-slim
MAINTAINER Falcon Framework Maintainers

RUN pip install --no-cache-dir falcon
RUN pip install --no-cache-dir bottle "django<2" flask
COPY ./benchmark.sh /benchmark.sh

CMD /benchmark.sh
