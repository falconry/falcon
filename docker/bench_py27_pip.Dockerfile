FROM python:2.7
MAINTAINER Falcon Framework Maintainers

RUN pip install falcon flask pecan bottle cherrypy
COPY ./benchmark.sh /benchmark.sh

CMD /benchmark.sh
