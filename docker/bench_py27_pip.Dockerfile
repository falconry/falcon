FROM python:2.7
MAINTAINER Falcon Framework Maintainers

RUN pip install falcon bottle django flask pecan
COPY ./benchmark.sh /benchmark.sh

CMD /benchmark.sh

