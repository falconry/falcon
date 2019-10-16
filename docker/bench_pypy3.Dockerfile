FROM pypy:3-slim
MAINTAINER Falcon Framework Maintainers

RUN pip install --no-cache-dir falcon
RUN pip install --no-cache-dir bottle "django" flask
COPY ./benchmark.sh benchmark.sh

CMD /benchmark.sh
