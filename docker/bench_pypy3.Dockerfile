FROM pypy:3.10-slim
LABEL org.opencontainers.image.authors="Falcon Framework Maintainers"

RUN pip install --upgrade pip
RUN pip install --no-cache-dir falcon
RUN pip install --no-cache-dir bottle Django Flask
COPY ./benchmark.sh benchmark.sh

CMD ["/benchmark.sh"]
